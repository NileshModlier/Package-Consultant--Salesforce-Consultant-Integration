"""Duplicate delivery, replay cursors, restart, and missed-event catch-up."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timezone

from integration.sf_client import HttpResponse
from integration.subscriber import (
    CHANNEL,
    REPLAY_NEW,
    CatchUpError,
    ReplayExpired,
    SalesforceCatchUp,
    SalesforceEventSource,
    StatusEvent,
    StatusSnapshot,
    StatusStore,
    StatusSubscriber,
)


def event(replay_id, status, owner="Inbound Sales", intake_ref="INT-20261124-0001", object_type="Lead"):
    return StatusEvent(replay_id, intake_ref, object_type, status, owner)


class ScriptedSource:
    def __init__(self, batches):
        self.calls = []
        self._batches = list(batches)

    def take(self, channel, replay_from):
        self.calls.append((channel, replay_from))
        item = self._batches.pop(0)
        if isinstance(item, Exception):
            raise item
        return [row for row in item if replay_from < 0 or row.replay_id > replay_from]


class ScriptedCatchUp:
    def __init__(self, snapshots):
        self.snapshots = list(snapshots)
        self.calls = []

    def fetch(self, since=None, refs=None):
        self.calls.append((since, list(refs) if refs else None))
        return list(self.snapshots)


class Token:
    def __init__(self, instance_url):
        self.value = "token-1"
        self.instance_url = instance_url


class FakeAuth:
    def __init__(self, transport, instance_url="https://example.my.salesforce.com"):
        self.transport = transport
        self.instance_url = instance_url

    def get_access_token(self):
        return Token(self.instance_url)


def bayeux(payload):
    return HttpResponse(200, {}, json.dumps(payload).encode("utf-8"))


class StatusSyncTests(unittest.TestCase):
    def test_duplicate_replay_id_is_applied_once(self):
        store = StatusStore(":memory:")
        duplicate = event(10, "Working - Contacted")
        source = ScriptedSource([[duplicate, duplicate]])
        stats = StatusSubscriber(store, source, ScriptedCatchUp([])).run_once()
        self.assertEqual(stats.applied, 1)
        self.assertEqual(stats.duplicates, 1)
        self.assertEqual(store.count(), 1)
        self.assertEqual(store.get("INT-20261124-0001", "Lead")["status"], "Working - Contacted")

        class Redeliver:
            def take(self, channel, replay_from):
                return [duplicate]

        again = StatusSubscriber(store, Redeliver(), ScriptedCatchUp([])).run_once()
        self.assertEqual(again.applied, 0)
        self.assertEqual(again.duplicates, 1)
        self.assertEqual(store.count(), 1)
        store.close()

    def test_replay_continues_after_the_stored_cursor(self):
        store = StatusStore(":memory:")
        first = ScriptedSource([[event(1, "Open - Not Contacted"), event(2, "Working - Contacted")]])
        StatusSubscriber(store, first, ScriptedCatchUp([])).run_once()
        self.assertEqual(first.calls, [(CHANNEL, REPLAY_NEW)])

        later = ScriptedSource(
            [[event(1, "Open - Not Contacted"), event(2, "Working - Contacted"), event(3, "Closed - Converted")]]
        )
        stats = StatusSubscriber(store, later, ScriptedCatchUp([])).run_once()
        self.assertEqual(later.calls, [(CHANNEL, 2)])
        self.assertEqual(stats.applied, 1)
        self.assertEqual(stats.duplicates, 0)
        self.assertEqual(store.get("INT-20261124-0001", "Lead")["status"], "Closed - Converted")
        self.assertEqual(store.get("INT-20261124-0001", "Lead")["replay_id"], 3)
        store.close()

    def test_restart_from_sqlite_skips_events_already_seen(self):
        handle = tempfile.NamedTemporaryFile(delete=False)
        handle.close()
        try:
            store = StatusStore(handle.name)
            StatusSubscriber(
                store,
                ScriptedSource([[event(4, "New", owner="Support Tier 1", intake_ref="INT-20261124-0011", object_type="Case")]]),
                ScriptedCatchUp([]),
            ).run_once()
            store.close()

            restarted = StatusStore(handle.name)
            source = ScriptedSource(
                [[
                    event(4, "New", owner="Support Tier 1", intake_ref="INT-20261124-0011", object_type="Case"),
                    event(5, "Working", owner="Support Tier 1", intake_ref="INT-20261124-0011", object_type="Case"),
                ]]
            )
            stats = StatusSubscriber(restarted, source, ScriptedCatchUp([])).run_once()
            self.assertEqual(source.calls, [(CHANNEL, 4)])
            self.assertEqual(stats.applied, 1)
            self.assertEqual(stats.duplicates, 0)
            self.assertEqual(restarted.count(), 1)
            self.assertEqual(restarted.get("INT-20261124-0011", "Case")["status"], "Working")
            restarted.close()
        finally:
            os.unlink(handle.name)

    def test_expired_replay_id_uses_catch_up_then_new_events(self):
        store = StatusStore(":memory:")
        store.apply_event(CHANNEL, event(8, "Open - Not Contacted", owner="Ada"))
        catchup = ScriptedCatchUp(
            [StatusSnapshot("INT-20261124-0001", "Lead", "Working - Contacted", "Inbound Sales")]
        )
        source = ScriptedSource(
            [
                ReplayExpired("replay id 8 expired"),
                [event(12, "Closed - Not Converted", owner="Inbound Sales")],
            ]
        )
        stats = StatusSubscriber(store, source, catchup).run_once()
        self.assertTrue(stats.replay_expired)
        self.assertEqual(stats.caught_up, 1)
        self.assertEqual(catchup.calls[0][1], ["INT-20261124-0001"])
        self.assertEqual(source.calls[1], (CHANNEL, REPLAY_NEW))
        self.assertEqual(stats.applied, 1)
        row = store.get("INT-20261124-0001", "Lead")
        self.assertEqual(row["status"], "Closed - Not Converted")
        self.assertEqual(row["owner_name"], "Inbound Sales")
        self.assertEqual(store.count(), 1)
        store.close()

    def test_cometd_batch_parses_replay_id_and_rejects_an_old_cursor(self):
        delivered = {
            "channel": CHANNEL,
            "data": {
                "payload": {
                    "Intake_Ref__c": "INT-20261124-0001",
                    "Object_Type__c": "Lead",
                    "Status__c": "Working - Contacted",
                    "Owner_Name__c": "Inbound Sales",
                },
                "event": {"replayId": 15},
            },
        }
        responses = [
            bayeux([{"channel": "/meta/handshake", "successful": True, "clientId": "abc"}]),
            bayeux([{"channel": "/meta/subscribe", "successful": True, "subscription": CHANNEL}]),
            bayeux([delivered]),
            bayeux([{"channel": "/meta/disconnect", "successful": True}]),
            bayeux([{"channel": "/meta/handshake", "successful": True, "clientId": "abc"}]),
            bayeux(
                [
                    {
                        "channel": "/meta/subscribe",
                        "successful": False,
                        "error": "400::The replayId you provided was invalid.",
                    }
                ]
            ),
            bayeux([{"channel": "/meta/disconnect", "successful": True}]),
        ]

        class QueueTransport:
            def __init__(self):
                self.bodies = []

            def __call__(self, method, url, headers, body, timeout):
                self.bodies.append(json.loads(body.decode("utf-8")))
                self.last_auth = headers["Authorization"]
                return responses.pop(0)

        transport = QueueTransport()
        source = SalesforceEventSource(FakeAuth(transport))
        events = source.take(CHANNEL, REPLAY_NEW)
        self.assertEqual(events, [event(15, "Working - Contacted")])
        subscribe = transport.bodies[1][0]
        self.assertEqual(subscribe["ext"]["replay"][CHANNEL], REPLAY_NEW)
        self.assertEqual(transport.last_auth, "Bearer token-1")

        with self.assertRaises(ReplayExpired):
            source.take(CHANNEL, 4)

    def test_catch_up_request_reads_the_apex_resource(self):
        payload = [
            {
                "intakeRef": "INT-20261124-0011",
                "objectType": "Case",
                "status": "New",
                "ownerName": "Support Tier 1",
            }
        ]

        def transport(method, url, headers, body, timeout):
            self.assertEqual(method, "GET")
            self.assertIn("/services/apexrest/intake/status?", url)
            self.assertIn("refs=INT-20261124-0011", url)
            self.assertIn("since=2026-11-24T12%3A00%3A00Z", url)
            self.assertEqual(headers["Authorization"], "Bearer token-1")
            self.assertIsNone(body)
            return HttpResponse(200, {}, json.dumps(payload).encode("utf-8"))

        rows = SalesforceCatchUp(FakeAuth(transport)).fetch(
            since=datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc),
            refs=["INT-20261124-0011"],
        )
        self.assertEqual(rows[0].object_type, "Case")
        self.assertEqual(rows[0].owner_name, "Support Tier 1")

        def failed(method, url, headers, body, timeout):
            return HttpResponse(400, {}, b'{"error":"Provide refs or since"}')

        with self.assertRaises(CatchUpError):
            SalesforceCatchUp(FakeAuth(failed)).fetch()


if __name__ == "__main__":
    unittest.main()
