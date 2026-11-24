"""Idempotent enqueue and upsert. Replaying a conversation must not create a second record."""

from __future__ import annotations

import json
import unittest
from datetime import datetime, timedelta, timezone

from integration.outbox import DEAD_LETTER, PENDING, SYNCED, Outbox, OutboxWorker, classify
from integration.sf_client import (
    EXTERNAL_ID_FIELD,
    HttpResponse,
    PermanentSalesforceError,
    RetryableSalesforceError,
    UpsertResult,
)
from tests.sample_conversations import SAMPLE_CONVERSATIONS


class MemorySalesforce:
    def __init__(self, failures=None):
        self.failures = list(failures or [])
        self.records = {}
        self.calls = []

    def upsert(self, sobject, external_id, record):
        self.calls.append((sobject, external_id, dict(record)))
        if self.failures:
            raise self.failures.pop(0)
        created = (sobject, external_id) not in self.records
        self.records[(sobject, external_id)] = dict(record)
        return UpsertResult(created=created, status_code=201 if created else 204)


class IdempotencyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
        self.outbox = Outbox(":memory:", clock=lambda: self.now)
        self.client = MemorySalesforce()
        self.worker = OutboxWorker(
            self.outbox,
            self.client,
            clock=lambda: self.now,
            backoff=lambda attempts, retry_after: 0,
        )

    def tearDown(self):
        self.outbox.close()

    def test_twenty_conversations_route_and_replay_without_duplicates(self):
        self.assertEqual(len(SAMPLE_CONVERSATIONS), 20)
        for conversation in SAMPLE_CONVERSATIONS:
            self.assertEqual(classify(conversation["transcript"]), conversation["expected"])
            self.outbox.accept_conversation(conversation)
            self.outbox.accept_conversation(conversation)

        self.assertEqual(sum(self.outbox.counts().values()), 20)
        self.assertEqual(self.outbox.counts()[PENDING], 20)

        first = self.worker.run_until_idle()
        self.assertEqual(first.synced, 20)
        self.assertEqual(len(self.client.records), 20)
        self.assertEqual(len(self.client.calls), 20)

        for conversation in SAMPLE_CONVERSATIONS:
            self.outbox.accept_conversation(conversation)
        second = self.worker.run_until_idle()
        self.assertEqual(second.processed, 0)
        self.assertEqual(len(self.client.records), 20)
        self.assertEqual(len(self.client.calls), 20)
        self.assertEqual(self.outbox.counts()[SYNCED], 20)

        refs = [ref for _, ref in self.client.records]
        self.assertEqual(len(refs), len(set(refs)))
        for conversation in SAMPLE_CONVERSATIONS:
            record = self.client.records[(conversation["expected"], conversation["intake_ref"])]
            self.assertNotIn("Status", record)
            self.assertNotIn("OwnerId", record)
            self.assertNotIn(EXTERNAL_ID_FIELD, record)
            self.assertEqual(record["Intake_Channel__c"], conversation["channel"])
            self.assertEqual(record["Intake_Summary__c"], conversation["summary"])
            if conversation["expected"] == "Lead":
                self.assertEqual(record["Company"], conversation["company"])
                self.assertIn("LastName", record)
            else:
                self.assertEqual(record["Priority"], conversation["priority"])
                self.assertLessEqual(len(record["Subject"]), 120)

    def test_retryable_failure_then_success_keeps_one_record(self):
        conversation = SAMPLE_CONVERSATIONS[0]
        self.outbox.accept_conversation(conversation)
        self.client.failures.append(RetryableSalesforceError("HTTP 503", status_code=503))

        first = self.worker.run_once()
        self.assertEqual(first.retrying, 1)
        self.assertEqual(self.outbox.counts()["Retrying"], 1)
        self.assertEqual(self.client.records, {})

        second = self.worker.run_once()
        self.assertEqual(second.synced, 1)
        self.assertEqual(len(self.client.records), 1)
        self.assertEqual(len(self.client.calls), 2)
        self.assertEqual(self.outbox.counts()[SYNCED], 1)

    def test_retry_after_waits(self):
        conversation = SAMPLE_CONVERSATIONS[1]
        self.outbox.accept_conversation(conversation)
        self.client.failures.append(
            RetryableSalesforceError("HTTP 429", status_code=429, retry_after=30)
        )
        waiting = OutboxWorker(self.outbox, self.client, clock=lambda: self.now)
        waiting.run_once()
        row = self.outbox.rows()[0]
        self.assertEqual(row["status"], "Retrying")
        self.assertEqual(row["next_attempt_at"], "2026-11-24T12:00:30Z")

        skipped = waiting.run_once()
        self.assertEqual(skipped.processed, 0)
        self.assertEqual(len(self.client.calls), 1)

        self.now = self.now + timedelta(seconds=30)
        waiting._clock = lambda: self.now
        self.outbox._clock = lambda: self.now
        done = waiting.run_once()
        self.assertEqual(done.synced, 1)
        self.assertEqual(len(self.client.records), 1)

    def test_repeated_429_becomes_dead_letter_without_a_record(self):
        conversation = SAMPLE_CONVERSATIONS[2]
        self.outbox.accept_conversation(conversation)
        self.client.failures = [
            RetryableSalesforceError("HTTP 429", status_code=429) for _ in range(5)
        ]
        stats = self.worker.run_until_idle()
        self.assertEqual(stats.dead_letter, 1)
        self.assertEqual(self.outbox.counts()[DEAD_LETTER], 1)
        self.assertEqual(self.client.records, {})
        self.assertEqual(self.outbox.rows()[0]["attempts"], 5)

        self.outbox.accept_conversation(conversation)
        again = self.worker.run_until_idle()
        self.assertEqual(again.processed, 0)
        self.assertEqual(len(self.client.calls), 5)

    def test_permanent_error_is_dead_letter_immediately(self):
        conversation = SAMPLE_CONVERSATIONS[10]
        self.outbox.accept_conversation(conversation)
        self.client.failures.append(
            PermanentSalesforceError("HTTP 400: Required field missing", status_code=400)
        )
        stats = self.worker.run_once()
        self.assertEqual(stats.dead_letter, 1)
        self.assertEqual(self.client.records, {})
        self.assertEqual(len(self.client.calls), 1)
        self.assertEqual(self.outbox.rows()[0]["attempts"], 1)

    def test_changed_payload_updates_the_same_external_id(self):
        conversation = dict(SAMPLE_CONVERSATIONS[3])
        self.outbox.accept_conversation(conversation)
        self.worker.run_until_idle()
        conversation["summary"] = "Send a revised quote for the annual plan."
        self.outbox.accept_conversation(conversation)
        self.worker.run_until_idle()
        self.assertEqual(len(self.client.records), 1)
        stored = self.client.records[("Lead", conversation["intake_ref"])]
        self.assertEqual(stored["Intake_Summary__c"], conversation["summary"])
        self.assertEqual(len(self.client.calls), 2)


class UpsertHttpTests(unittest.TestCase):
    def test_same_external_id_is_updated_in_place(self):
        from integration.sf_auth import SalesforceAuth
        from integration.sf_client import SalesforceClient

        token_body = json.dumps(
            {
                "access_token": "token-1",
                "instance_url": "https://example.my.salesforce.com",
                "expires_in": 3600,
            }
        ).encode()
        created = {}
        calls = []

        def transport(method, url, headers, body, timeout):
            calls.append(method)
            if method == "POST":
                self.assertIn(b"grant_type=client_credentials", body)
                self.assertIn(b"client_id=client", body)
                self.assertNotIn("Authorization", headers)
                return HttpResponse(200, {}, token_body)
            key = url.rsplit("/", 1)[-1]
            record = json.loads(body.decode())
            first = key not in created
            created[key] = record
            self.assertIn(f"/sobjects/Lead/{EXTERNAL_ID_FIELD}/", url)
            self.assertEqual(headers["Authorization"], "Bearer token-1")
            self.assertNotIn(EXTERNAL_ID_FIELD, record)
            return HttpResponse(201 if first else 204, {}, b"")

        auth = SalesforceAuth("client", "secret", "https://example.my.salesforce.com/services/oauth2/token", transport)
        client = SalesforceClient(auth)
        record = {"LastName": "Lee", "Company": "Northline Analytics"}
        first = client.upsert("Lead", "INT-20261124-0001", record)
        second = client.upsert("Lead", "INT-20261124-0001", record)
        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(len(created), 1)
        self.assertEqual(calls.count("POST"), 1)
        self.assertEqual(calls.count("PATCH"), 2)


if __name__ == "__main__":
    unittest.main()
