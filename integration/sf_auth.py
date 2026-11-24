"""OAuth client credentials for a Salesforce External Client App.

The org side is an External Client App with the client credentials flow enabled
and a run-as user. This module only requests and caches the access token.

Environment variables:

- SF_CLIENT_ID
- SF_CLIENT_SECRET
- SF_TOKEN_URL: full token endpoint, usually
  https://<my-domain>/services/oauth2/token
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from integration.retry_matrix import BACKOFF, DEAD_LETTER, REFRESH_ONCE, RETRY, action_for_status
from integration.sf_client import (
    HttpResponse,
    NetworkError,
    PermanentSalesforceError,
    RetryableSalesforceError,
)


class HttpTransport(Protocol):
    def request(
        self,
        method: str,
        url: str,
        headers: Mapping[str, str],
        body: bytes | None,
        timeout: float,
    ) -> HttpResponse:
        """Perform one HTTP call and return the response, including error statuses."""


def urllib_transport(
    method: str,
    url: str,
    headers: Mapping[str, str],
    body: bytes | None,
    timeout: float,
) -> HttpResponse:
    request = Request(url, data=body, headers=dict(headers), method=method)
    try:
        with urlopen(request, timeout=timeout) as response:
            raw_headers = {key.lower(): value for key, value in response.headers.items()}
            return HttpResponse(status=response.status, headers=raw_headers, body=response.read())
    except HTTPError as error:
        raw_headers = {key.lower(): value for key, value in error.headers.items()} if error.headers else {}
        return HttpResponse(status=error.code, headers=raw_headers, body=error.read())
    except (URLError, TimeoutError, OSError) as error:
        raise NetworkError(str(error)) from error


@dataclass
class AccessToken:
    value: str
    instance_url: str
    expires_at: datetime


class SalesforceAuth:
    """Client credentials grant. The secret stays in memory and is never logged."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        token_url: str,
        transport: HttpTransport | None = None,
        timeout: float = 30,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not client_id or not client_secret or not token_url:
            raise ValueError("client_id, client_secret, and token_url are required")
        self._client_id = client_id
        self._client_secret = client_secret
        self._token_url = token_url
        self._transport = transport or urllib_transport
        self._timeout = timeout
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._cached: AccessToken | None = None

    @classmethod
    def from_env(cls) -> "SalesforceAuth":
        missing = [
            name
            for name in ("SF_CLIENT_ID", "SF_CLIENT_SECRET", "SF_TOKEN_URL")
            if not os.environ.get(name)
        ]
        if missing:
            raise ValueError("Missing environment variables: " + ", ".join(missing))
        return cls(
            client_id=os.environ["SF_CLIENT_ID"],
            client_secret=os.environ["SF_CLIENT_SECRET"],
            token_url=os.environ["SF_TOKEN_URL"],
        )

    @property
    def transport(self) -> HttpTransport:
        return self._transport

    def invalidate(self) -> None:
        self._cached = None

    def get_access_token(self) -> AccessToken:
        now = self._clock()
        if self._cached and self._cached.expires_at - timedelta(seconds=60) > now:
            return self._cached
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            }
        ).encode("utf-8")
        try:
            response = self._transport(
                "POST",
                self._token_url,
                {"Content-Type": "application/x-www-form-urlencoded", "Accept": "application/json"},
                body,
                self._timeout,
            )
        except NetworkError:
            raise
        action = action_for_status(response.status)
        if action in (RETRY, BACKOFF):
            raise RetryableSalesforceError(
                f"Token request failed with HTTP {response.status}",
                status_code=response.status,
                retry_after=_retry_after(response.headers),
            )
        if action in (REFRESH_ONCE, DEAD_LETTER) or response.status != 200:
            raise PermanentSalesforceError(
                f"Token request failed with HTTP {response.status}",
                status_code=response.status,
            )
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PermanentSalesforceError("Token response was not JSON") from error
        token = payload.get("access_token")
        instance_url = payload.get("instance_url")
        if not token or not instance_url:
            raise PermanentSalesforceError("Token response did not include access_token and instance_url")
        expires_in = payload.get("expires_in", 3600)
        try:
            lifetime = int(expires_in)
        except (TypeError, ValueError):
            lifetime = 3600
        self._cached = AccessToken(
            value=str(token),
            instance_url=str(instance_url).rstrip("/"),
            expires_at=now + timedelta(seconds=lifetime),
        )
        return self._cached


def _retry_after(headers: Mapping[str, str]) -> float | None:
    raw = headers.get("retry-after")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None
