"""Unit checks for the retry decision table and the status dashboard."""

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone

from integration.monitor import format_dashboard, snapshot
from integration.outbox import DEAD_LETTER, PENDING, RETRYING, SYNCED, Outbox, OutboxWorker
from integration.retry_matrix import (
    BACKOFF,
    DEAD_LETTER as DEAD_ACTION,
    MAX_ATTEMPTS,
    REFRESH_ONCE,
    RETRY,
    SUCCESS,
    RetryRule,
    RETRY_MATRIX,
    action_for_status,
    backoff_seconds,
)
from integration.sf_client import PermanentSalesforceError, RetryableSalesforceError, UpsertResult
from integration.subscriber import CHANNEL, StatusEvent, StatusStore
from tests.sample_conversations import SAMPLE_CONVERSATIONS


class MatrixTests(unittest.TestCase):
    def test_each_listed_signal_maps_to_one_action(self):
        signals = [rule.signal for rule in RETRY_MATRIX]
        self.assertEqual(len(signals), len(set(signals)))
        self.assertIsInstance(RETRY_MATRIX[0], RetryRule)
        self.assertEqual(action_for_status(401), REFRESH_ONCE)
        self.assertEqual(action_for_status(408), RETRY)
        self.assertEqual(action_for_status(429), BACKOFF)
        for status in (500, 503, 599):
            self.assertEqual(action_for_status(status), RETRY)
        for status in (400, 403, 404, 422):
            self.assertEqual(action_for_status(status), DEAD_ACTION)
        self.assertEqual(action_for_status(201), SUCCESS)
        self.assertEqual(MAX_ATTEMPTS, 5)

    def test_429_uses_retry_after_and_other_retries_double(self):
        self.assertEqual(backoff_seconds(1, 30), 30)
        self.assertEqual(backoff_seconds(1, None), 1)
        self.assertEqual(backoff_seconds(2, None), 2)
        self.assertEqual(backoff_seconds(3, None), 4)
        self.assertEqual(backoff_seconds(4, None), 8)
        self.assertEqual(backoff_seconds(10, None), 60)


class MemorySalesforce:
    def __init__(self, failures=None):
        self.failures = list(failures or [])
        self.calls = 0

    def upsert(self, sobject, external_id, record):
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return UpsertResult(created=True, status_code=201)


class DashboardTests(unittest.TestCase):
    def test_snapshot_counts_queue_retries_and_dead_letters(self):
        now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
        clock = {"now": now}
        outbox = Outbox(":memory:", clock=lambda: clock["now"])
        lead = SAMPLE_CONVERSATIONS[1]
        case_limit = SAMPLE_CONVERSATIONS[11]
        case_invalid = SAMPLE_CONVERSATIONS[12]
        waiting = SAMPLE_CONVERSATIONS[0]
        client = MemorySalesforce()
        worker = OutboxWorker(outbox, client, clock=lambda: clock["now"])

        outbox.accept_conversation(lead)
        worker.run_once()

        client.failures = [RetryableSalesforceError("HTTP 429: limit", status_code=429, retry_after=30)]
        outbox.accept_conversation(case_limit)
        worker.run_once()

        client.failures = [PermanentSalesforceError("HTTP 400: Priority is required", status_code=400)]
        outbox.accept_conversation(case_invalid)
        worker.run_once()

        outbox.accept_conversation(waiting)

        store = StatusStore(":memory:", clock=lambda: now)
        store.apply_event(
            CHANNEL,
            StatusEvent(4, lead["intake_ref"], "Lead", "Working - Contacted", "Inbound Sales"),
        )
        board = snapshot(outbox, store)
        text = format_dashboard(board)

        self.assertEqual(board.pending, 1)
        self.assertEqual(board.retrying, 1)
        self.assertEqual(board.synced, 1)
        self.assertEqual(board.dead_letter, 1)
        self.assertEqual(board.retry_attempts, 1)
        self.assertEqual(board.status_rows, 1)
        self.assertEqual(board.replay_cursor, 4)
        self.assertIsNone(board.subscriber_error)
        self.assertEqual(board.dead_letters[0].intake_ref, case_invalid["intake_ref"])
        self.assertEqual(board.dead_letters[0].attempts, 1)
        self.assertIn("Priority is required", board.dead_letters[0].last_error)
        retry_row = [row for row in outbox.rows() if row["status"] == RETRYING][0]
        self.assertEqual(retry_row["next_attempt_at"], "2026-11-24T12:00:30Z")
        self.assertIn("Pending 1", text)
        self.assertIn("Dead Letter 1", text)
        ready = [row["intake_ref"] for row in outbox.ready(now + timedelta(seconds=29))]
        self.assertNotIn(case_limit["intake_ref"], ready)
        self.assertIn(waiting["intake_ref"], ready)
        outbox.close()
        store.close()


if __name__ == "__main__":
    unittest.main()
