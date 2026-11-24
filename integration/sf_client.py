"""Salesforce REST client. Upsert by external id only.

Writes use PATCH /sobjects/{Object}/Intake_Ref__c/{value}. A second write with the
same reference updates that record. This client does not publish Platform Events
and does not read or write record status.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Mapping
from urllib.error import URLError
from urllib.parse import quote

from integration.retry_matrix import BACKOFF, DEAD_LETTER, REFRESH_ONCE, RETRY, action_for_status

EXTERNAL_ID_FIELD = "Intake_Ref__c"


class SalesforceError(Exception):
    def __init__(self, message: str, status_code: int | None = None, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


class RetryableSalesforceError(SalesforceError):
    """408, 429, 5xx, or a network failure. The outbox may try again."""


class PermanentSalesforceError(SalesforceError):
    """The same request will fail again. The outbox dead-letters it."""


class NetworkError(RetryableSalesforceError):
    """The request did not receive an HTTP response."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    headers: Mapping[str, str]
    body: bytes


@dataclass(frozen=True)
class UpsertResult:
    created: bool
    status_code: int


class SalesforceClient:
    def __init__(
        self,
        auth: object,
        api_version: str | None = None,
        timeout: float = 30,
    ) -> None:
        import os

        self._auth = auth
        self._api_version = api_version or os.environ.get("SF_API_VERSION", "62.0")
        self._timeout = timeout

    def upsert(self, sobject: str, external_id: str, record: Mapping[str, object]) -> UpsertResult:
        if not external_id:
            raise PermanentSalesforceError("External id is required")
        return self._upsert_once(sobject, external_id, record, allow_refresh=True)

    def _upsert_once(
        self,
        sobject: str,
        external_id: str,
        record: Mapping[str, object],
        allow_refresh: bool,
    ) -> UpsertResult:
        token = self._auth.get_access_token()
        url = (
            f"{token.instance_url}/services/data/v{self._api_version}/sobjects/"
            f"{sobject}/{EXTERNAL_ID_FIELD}/{quote(external_id, safe='')}"
        )
        body = json.dumps(dict(record)).encode("utf-8")
        try:
            response = self._auth.transport(
                "PATCH",
                url,
                {
                    "Authorization": f"Bearer {token.value}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                body,
                self._timeout,
            )
        except NetworkError:
            raise
        except (URLError, TimeoutError, OSError) as error:
            raise NetworkError(str(error)) from error
        action = action_for_status(response.status)
        if action == REFRESH_ONCE and allow_refresh:
            self._auth.invalidate()
            return self._upsert_once(sobject, external_id, record, allow_refresh=False)
        if action in (RETRY, BACKOFF):
            raise RetryableSalesforceError(
                _error_message(response),
                status_code=response.status,
                retry_after=_retry_after(response.headers),
            )
        if action == DEAD_LETTER or action == REFRESH_ONCE:
            raise PermanentSalesforceError(_error_message(response), status_code=response.status)
        if response.status not in (200, 201, 204):
            raise PermanentSalesforceError(
                f"Unexpected HTTP {response.status}",
                status_code=response.status,
            )
        return UpsertResult(created=response.status == 201, status_code=response.status)


def _retry_after(headers: Mapping[str, str]) -> float | None:
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def _error_message(response: HttpResponse) -> str:
    text = response.body.decode("utf-8", errors="replace").strip()
    if not text:
        return f"Salesforce returned HTTP {response.status}"
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return f"HTTP {response.status}: {text[:500]}"
    if isinstance(payload, list) and payload:
        first = payload[0]
        if isinstance(first, dict):
            message = first.get("message") or first.get("errorCode") or text
            return f"HTTP {response.status}: {message}"
    if isinstance(payload, dict):
        message = payload.get("message") or payload.get("error_description") or payload.get("error")
        if message:
            return f"HTTP {response.status}: {message}"
    return f"HTTP {response.status}: {text[:500]}"
