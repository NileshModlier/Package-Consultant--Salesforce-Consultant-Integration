"""How a failed Salesforce call moves an outbox row.

401 on an API call refreshes the access token once inside the client. The
outbox does not see that attempt. A second 401, a validation error, or a
rejected client secret is Dead Letter. 408, 429, 5xx, and network failures
become Retrying until the fifth attempt.
"""

from __future__ import annotations

from dataclasses import dataclass

REFRESH_ONCE = "refresh_once"
RETRY = "retry"
BACKOFF = "backoff"
DEAD_LETTER = "dead_letter"
SUCCESS = "success"

MAX_ATTEMPTS = 5
BACKOFF_CAP_SECONDS = 60


@dataclass(frozen=True)
class RetryRule:
    signal: str
    action: str
    outbox_state: str
    schedule: str


RETRY_MATRIX: tuple[RetryRule, ...] = (
    RetryRule(
        "401",
        "Refresh the access token once",
        "Unchanged if the new token succeeds",
        "One new token request. A second 401 is Dead Letter.",
    ),
    RetryRule(
        "408",
        "Retry",
        "Retrying",
        "1s, 2s, 4s, 8s, then Dead Letter on attempt 5. Cap 60s.",
    ),
    RetryRule(
        "429",
        "Backoff",
        "Retrying",
        "Retry-After when Salesforce sends it. Otherwise the 408 schedule.",
    ),
    RetryRule(
        "5xx",
        "Retry",
        "Retrying",
        "Same schedule as 408.",
    ),
    RetryRule(
        "400 validation",
        "Dead Letter",
        "Dead Letter",
        "Immediate. Other 4xx except 401, 408, and 429 follow this rule.",
    ),
    RetryRule(
        "Network failure",
        "Retry",
        "Retrying",
        "Same schedule as 408. No HTTP status was received.",
    ),
    RetryRule(
        "Wrong client secret",
        "Dead Letter",
        "Dead Letter",
        "The token endpoint rejects the secret. There is no token to refresh.",
    ),
)


def action_for_status(status: int) -> str:
    """Return the matrix action for one HTTP status."""
    if 200 <= status <= 299:
        return SUCCESS
    if status == 401:
        return REFRESH_ONCE
    if status == 429:
        return BACKOFF
    if status == 408 or 500 <= status <= 599:
        return RETRY
    if status >= 400:
        return DEAD_LETTER
    return DEAD_LETTER


def backoff_seconds(attempts: int, retry_after: float | None) -> float:
    """Seconds until the next delivery. A 429 header wins over the exponential schedule."""
    if retry_after is not None and retry_after >= 0:
        return float(retry_after)
    if attempts < 1:
        return 0.0
    return float(min(BACKOFF_CAP_SECONDS, 2 ** (attempts - 1)))
