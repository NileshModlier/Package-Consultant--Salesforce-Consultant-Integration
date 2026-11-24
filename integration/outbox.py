"""Durable outbox from an intake conversation to a Salesforce Lead or Case.

Sales inquiry conversations become a Lead. Support request conversations become
a Case. Both are upserted by Intake_Ref__c. Replaying the same conversation does
not create a second outbox row or a second Salesforce record.

States are Pending, Retrying, Synced, and Dead Letter.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping

from integration.retry_matrix import MAX_ATTEMPTS, backoff_seconds
from integration.sf_client import (
    EXTERNAL_ID_FIELD,
    PermanentSalesforceError,
    RetryableSalesforceError,
    SalesforceClient,
)

PENDING = "Pending"
RETRYING = "Retrying"
SYNCED = "Synced"
DEAD_LETTER = "Dead Letter"

SALES_INTENT = "sales inquiry"
SUPPORT_INTENT = "support request"
CASE_PRIORITIES = {"High", "Medium", "Low"}


class RouteError(ValueError):
    """The conversation did not match exactly one business route."""


@dataclass
class WorkerStats:
    processed: int = 0
    synced: int = 0
    retrying: int = 0
    dead_letter: int = 0

    def add(self, other: "WorkerStats") -> None:
        self.processed += other.processed
        self.synced += other.synced
        self.retrying += other.retrying
        self.dead_letter += other.dead_letter


def classify(transcript: str) -> str:
    """Return Lead for a sales inquiry and Case for a support request."""
    text = transcript.lower()
    sales = SALES_INTENT in text
    support = SUPPORT_INTENT in text
    if sales and not support:
        return "Lead"
    if support and not sales:
        return "Case"
    if sales and support:
        raise RouteError("Conversation matches both a sales inquiry and a support request")
    raise RouteError("Conversation matches neither a sales inquiry nor a support request")


def build_payload(conversation: Mapping[str, str], sobject: str) -> dict[str, str]:
    """Fields for one upsert. Status and OwnerId are omitted so a replay cannot reset them."""
    summary = " ".join(str(conversation.get("summary") or "").split())
    if not summary:
        raise RouteError("Summary is required")
    channel = str(conversation.get("channel") or "").strip()
    if channel not in {"Web", "Email", "Chat", "Phone"}:
        raise RouteError("Channel must be Web, Email, Chat, or Phone")
    email = str(conversation.get("email") or "").strip()
    name = " ".join(str(conversation.get("name") or "").split())
    company = " ".join(str(conversation.get("company") or "").split())
    first_name, last_name = _split_name(name)
    if sobject == "Lead":
        if not last_name or not company or not email:
            raise RouteError("A sales inquiry needs a name, company, and email")
        payload = {
            "FirstName": first_name,
            "LastName": last_name,
            "Company": company,
            "Email": email,
            "Intake_Summary__c": summary,
            "Intake_Channel__c": channel,
        }
        if not first_name:
            del payload["FirstName"]
        return payload
    priority = _case_priority(conversation)
    supplied = {
        "Subject": _subject(summary),
        "Priority": priority,
        "Intake_Summary__c": summary,
        "Intake_Channel__c": channel,
    }
    if email:
        supplied["SuppliedEmail"] = email
    if name:
        supplied["SuppliedName"] = name
    if company:
        supplied["SuppliedCompany"] = company
    return supplied


class Outbox:
    def __init__(self, db_path: str = "intake_outbox.sqlite", clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                intake_ref TEXT NOT NULL,
                object_api_name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                status TEXT NOT NULL,
                attempts INTEGER NOT NULL DEFAULT 0,
                next_attempt_at TEXT,
                last_error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE (intake_ref, object_api_name)
            )
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def accept_conversation(self, conversation: Mapping[str, str]) -> str:
        """Store one conversation. The same intake reference and route is stored once."""
        intake_ref = str(conversation.get("intake_ref") or "").strip()
        if not _valid_ref(intake_ref):
            raise RouteError("Intake ref must use INT-YYYYMMDD-####")
        sobject = classify(str(conversation.get("transcript") or ""))
        payload = build_payload(conversation, sobject)
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        now = _iso(self._clock())
        existing = self._conn.execute(
            "SELECT id, payload_json, status FROM outbox WHERE intake_ref = ? AND object_api_name = ?",
            (intake_ref, sobject),
        ).fetchone()
        if existing is None:
            self._conn.execute(
                """
                INSERT INTO outbox (
                    intake_ref, object_api_name, payload_json, status, attempts,
                    next_attempt_at, last_error, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 0, NULL, NULL, ?, ?)
                """,
                (intake_ref, sobject, canonical, PENDING, now, now),
            )
            self._conn.commit()
            return PENDING
        if existing["payload_json"] == canonical or existing["status"] == DEAD_LETTER:
            return str(existing["status"])
        self._conn.execute(
            """
            UPDATE outbox
            SET payload_json = ?, status = ?, attempts = 0, next_attempt_at = NULL,
                last_error = NULL, updated_at = ?
            WHERE id = ?
            """,
            (canonical, PENDING, now, existing["id"]),
        )
        self._conn.commit()
        return PENDING

    def ready(self, now: datetime | None = None) -> list[sqlite3.Row]:
        moment = _iso(now or self._clock())
        return list(
            self._conn.execute(
                """
                SELECT * FROM outbox
                WHERE status IN (?, ?)
                  AND (next_attempt_at IS NULL OR next_attempt_at <= ?)
                ORDER BY id
                """,
                (PENDING, RETRYING, moment),
            )
        )

    def counts(self) -> dict[str, int]:
        rows = self._conn.execute("SELECT status, COUNT(*) AS n FROM outbox GROUP BY status")
        found = {row["status"]: row["n"] for row in rows}
        return {status: found.get(status, 0) for status in (PENDING, RETRYING, SYNCED, DEAD_LETTER)}

    def retry_attempts(self) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(attempts), 0) AS n FROM outbox WHERE status = ?",
            (RETRYING,),
        ).fetchone()
        return int(row["n"])

    def dead_letter_rows(self) -> list[sqlite3.Row]:
        return list(
            self._conn.execute(
                """
                SELECT intake_ref, object_api_name, attempts, last_error
                FROM outbox
                WHERE status = ?
                ORDER BY id
                """,
                (DEAD_LETTER,),
            )
        )

    def rows(self) -> list[sqlite3.Row]:
        return list(self._conn.execute("SELECT * FROM outbox ORDER BY id"))

    def mark_synced(self, row_id: int) -> None:
        self._set_status(row_id, SYNCED, None, keep_attempts=True)

    def mark_retrying(self, row_id: int, attempts: int, next_attempt_at: datetime, error: str) -> None:
        now = _iso(self._clock())
        self._conn.execute(
            """
            UPDATE outbox
            SET status = ?, attempts = ?, next_attempt_at = ?, last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (RETRYING, attempts, _iso(next_attempt_at), error[:1000], now, row_id),
        )
        self._conn.commit()

    def mark_dead_letter(self, row_id: int, attempts: int, error: str) -> None:
        now = _iso(self._clock())
        self._conn.execute(
            """
            UPDATE outbox
            SET status = ?, attempts = ?, next_attempt_at = NULL, last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (DEAD_LETTER, attempts, error[:1000], now, row_id),
        )
        self._conn.commit()

    def _set_status(self, row_id: int, status: str, error: str | None, keep_attempts: bool) -> None:
        now = _iso(self._clock())
        self._conn.execute(
            """
            UPDATE outbox
            SET status = ?, next_attempt_at = NULL, last_error = ?, updated_at = ?
            WHERE id = ?
            """,
            (status, error, now, row_id),
        )
        self._conn.commit()


class OutboxWorker:
    def __init__(
        self,
        outbox: Outbox,
        client: SalesforceClient,
        max_attempts: int = MAX_ATTEMPTS,
        clock: Callable[[], datetime] | None = None,
        backoff: Callable[[int, float | None], float] | None = None,
    ) -> None:
        self._outbox = outbox
        self._client = client
        self._max_attempts = max_attempts
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._backoff = backoff or backoff_seconds

    def run_once(self) -> WorkerStats:
        stats = WorkerStats()
        for row in self._outbox.ready(self._clock()):
            stats.processed += 1
            payload = json.loads(row["payload_json"])
            try:
                self._client.upsert(row["object_api_name"], row["intake_ref"], payload)
            except RetryableSalesforceError as error:
                attempts = int(row["attempts"]) + 1
                if attempts >= self._max_attempts:
                    self._outbox.mark_dead_letter(row["id"], attempts, str(error))
                    stats.dead_letter += 1
                else:
                    delay = self._backoff(attempts, error.retry_after)
                    self._outbox.mark_retrying(
                        row["id"],
                        attempts,
                        self._clock() + timedelta(seconds=delay),
                        str(error),
                    )
                    stats.retrying += 1
            except PermanentSalesforceError as error:
                attempts = int(row["attempts"]) + 1
                self._outbox.mark_dead_letter(row["id"], attempts, str(error))
                stats.dead_letter += 1
            else:
                self._outbox.mark_synced(row["id"])
                stats.synced += 1
        return stats

    def run_until_idle(self) -> WorkerStats:
        total = WorkerStats()
        while True:
            stats = self.run_once()
            total.add(stats)
            if stats.processed == 0:
                return total


def _case_priority(conversation: Mapping[str, str]) -> str:
    raw = str(conversation.get("priority") or "").strip().title()
    if raw in CASE_PRIORITIES:
        return raw
    text = str(conversation.get("transcript") or "").lower()
    if any(word in text for word in ("urgent", "outage", "critical")):
        return "High"
    return "Medium"


def _split_name(name: str) -> tuple[str, str]:
    if not name:
        return "", ""
    first, _, rest = name.partition(" ")
    if not rest:
        return "", first
    return first, rest


def _subject(summary: str) -> str:
    if len(summary) <= 120:
        return summary
    return summary[:117].rstrip() + "..."


def _valid_ref(value: str) -> bool:
    if len(value) != 17 or not value.startswith("INT-"):
        return False
    date_part, _, sequence = value[4:].partition("-")
    return len(date_part) == 8 and date_part.isdigit() and len(sequence) == 4 and sequence.isdigit()


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Re-exported so callers can see which external id the upsert uses.
OUTBOX_EXTERNAL_ID_FIELD = EXTERNAL_ID_FIELD


def main() -> None:
    """Deliver ready outbox rows. Requires SF_CLIENT_ID, SF_CLIENT_SECRET, and SF_TOKEN_URL."""
    from integration.sf_auth import SalesforceAuth

    worker = OutboxWorker(
        Outbox(os.environ.get("INTAKE_OUTBOX_PATH", "intake_outbox.sqlite")),
        SalesforceClient(SalesforceAuth.from_env()),
    )
    stats = worker.run_once()
    print(
        f"processed={stats.processed} synced={stats.synced} "
        f"retrying={stats.retrying} dead_letter={stats.dead_letter}"
    )


if __name__ == "__main__":
    main()
