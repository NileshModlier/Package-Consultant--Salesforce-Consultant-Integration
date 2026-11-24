"""Fault injection for the six recovery cases. Each drill records what the sync did."""

from __future__ import annotations

import json
import socket
import threading
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, unquote

from integration.outbox import DEAD_LETTER, RETRYING, SYNCED, Outbox, OutboxWorker
from integration.sf_auth import SalesforceAuth, urllib_transport
from integration.sf_client import (
    EXTERNAL_ID_FIELD,
    NetworkError,
    SalesforceClient,
)
from integration.subscriber import (
    CHANNEL,
    SalesforceEventSource,
    StatusEvent,
    StatusStore,
    StatusSubscriber,
)
from tests.sample_conversations import SAMPLE_CONVERSATIONS


@dataclass(frozen=True)
class DrillResult:
    name: str
    fault: str
    observed: str
    ok: bool


class FaultStandIn(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(body)
        self.server.token_calls += 1
        if self.server.reject_secret or form.get("client_secret", [""])[0] == "wrong-secret":
            self._send(401, b'{"error":"invalid_client","error_description":"invalid client credentials"}')
            return
        port = self.server.server_address[1]
        payload = json.dumps(
            {
                "access_token": f"token-{self.server.token_calls}",
                "instance_url": f"http://127.0.0.1:{port}",
                "expires_in": 3600,
            }
        ).encode("utf-8")
        self._send(200, payload)

    def do_PATCH(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        self.server.patch_calls += 1
        if self.server.patch_script:
            status, headers, body = self.server.patch_script.pop(0)
            self._send(status, body, headers)
            return
        parts = [unquote(part) for part in self.path.split("/")]
        key = (parts[5], parts[7])
        created = key not in self.server.records
        self.server.records[key] = json.loads(raw.decode("utf-8"))
        self._send(201 if created else 204, b"")

    def _send(self, status, body, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


class StandIn:
    def __init__(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), FaultStandIn)
        self.server.token_calls = 0
        self.server.patch_calls = 0
        self.server.reject_secret = False
        self.server.patch_script = []
        self.server.records = {}
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        port = self.server.server_address[1]
        self.auth = SalesforceAuth(
            "intake-client",
            "intake-secret",
            f"http://127.0.0.1:{port}/services/oauth2/token",
            transport=urllib_transport,
            timeout=2,
        )
        self.client = SalesforceClient(self.auth, api_version="62.0", timeout=2)

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def _closed_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _clock_at(moment):
    return lambda: moment


def drill_wrong_secret() -> DrillResult:
    standin = StandIn()
    now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
    outbox = Outbox(":memory:", clock=_clock_at(now))
    try:
        standin.server.reject_secret = True
        outbox.accept_conversation(SAMPLE_CONVERSATIONS[0])
        stats = OutboxWorker(outbox, standin.client, clock=_clock_at(now)).run_once()
        row = outbox.rows()[0]
        observed = (
            f"state={row['status']} attempts={row['attempts']} "
            f"token_calls={standin.server.token_calls} patch_calls={standin.server.patch_calls} "
            f"dead_letter={stats.dead_letter}"
        )
        ok = (
            row["status"] == DEAD_LETTER
            and row["attempts"] == 1
            and standin.server.token_calls == 1
            and standin.server.patch_calls == 0
            and stats.dead_letter == 1
            and "401" in (row["last_error"] or "")
        )
        return DrillResult("Wrong secret", "Token endpoint 401 invalid_client", observed, ok)
    finally:
        outbox.close()
        standin.close()


def drill_network_failure() -> DrillResult:
    now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
    outbox = Outbox(":memory:", clock=_clock_at(now))
    standin = StandIn()
    try:
        port = _closed_port()
        refused = SalesforceAuth(
            "intake-client",
            "intake-secret",
            f"http://127.0.0.1:{port}/services/oauth2/token",
            transport=urllib_transport,
            timeout=2,
        )
        outbox.accept_conversation(SAMPLE_CONVERSATIONS[0])
        first = OutboxWorker(
            outbox,
            SalesforceClient(refused, timeout=2),
            clock=_clock_at(now),
            backoff=lambda attempts, retry_after: 0,
        ).run_once()
        after_failure = outbox.rows()[0]["status"]
        second = OutboxWorker(outbox, standin.client, clock=_clock_at(now)).run_once()
        after_recovery = outbox.rows()[0]["status"]
        observed = (
            f"after_refusal={after_failure} retrying={first.retrying} "
            f"after_recovery={after_recovery} synced={second.synced} records={len(standin.server.records)}"
        )
        ok = (
            after_failure == RETRYING
            and first.retrying == 1
            and after_recovery == SYNCED
            and second.synced == 1
            and len(standin.server.records) == 1
        )
        return DrillResult("Network failure", "Connection refused, then a live token endpoint", observed, ok)
    finally:
        outbox.close()
        standin.close()


def drill_validation_failure() -> DrillResult:
    standin = StandIn()
    now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
    outbox = Outbox(":memory:", clock=_clock_at(now))
    try:
        standin.server.patch_script = [
            (400, {}, b'[{"message":"Priority is required","errorCode":"FIELD_CUSTOM_VALIDATION_EXCEPTION"}]')
        ]
        outbox.accept_conversation(SAMPLE_CONVERSATIONS[11])
        worker = OutboxWorker(outbox, standin.client, clock=_clock_at(now))
        stats = worker.run_once()
        again = worker.run_once()
        row = outbox.rows()[0]
        observed = (
            f"state={row['status']} attempts={row['attempts']} "
            f"patch_calls={standin.server.patch_calls} second_pass={again.processed}"
        )
        ok = (
            stats.dead_letter == 1
            and row["status"] == DEAD_LETTER
            and row["attempts"] == 1
            and standin.server.patch_calls == 1
            and again.processed == 0
            and "Priority is required" in (row["last_error"] or "")
        )
        return DrillResult("Validation failure", "PATCH 400 field validation", observed, ok)
    finally:
        outbox.close()
        standin.close()


def drill_duplicate_submission() -> DrillResult:
    standin = StandIn()
    now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
    outbox = Outbox(":memory:", clock=_clock_at(now))
    try:
        conversation = SAMPLE_CONVERSATIONS[0]
        first_state = outbox.accept_conversation(conversation)
        second_state = outbox.accept_conversation(conversation)
        worker = OutboxWorker(outbox, standin.client, clock=_clock_at(now))
        worker.run_until_idle()
        replay_state = outbox.accept_conversation(conversation)
        replay = worker.run_until_idle()
        observed = (
            f"enqueue={first_state} duplicate_enqueue={second_state} rows={len(outbox.rows())} "
            f"records={len(standin.server.records)} replay={replay_state} replay_processed={replay.processed}"
        )
        ok = (
            len(outbox.rows()) == 1
            and len(standin.server.records) == 1
            and replay.processed == 0
            and outbox.counts()[SYNCED] == 1
            and (conversation["expected"], conversation["intake_ref"]) in standin.server.records
        )
        return DrillResult("Duplicate submission", "Same conversation accepted twice and replayed", observed, ok)
    finally:
        outbox.close()
        standin.close()


def drill_api_limit() -> DrillResult:
    standin = StandIn()
    now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
    clock = {"now": now}
    outbox = Outbox(":memory:", clock=lambda: clock["now"])
    try:
        standin.server.patch_script = [
            (
                429,
                {"Retry-After": "30"},
                b'[{"message":"Request limit exceeded","errorCode":"REQUEST_LIMIT_EXCEEDED"}]',
            )
        ]
        outbox.accept_conversation(SAMPLE_CONVERSATIONS[11])
        worker = OutboxWorker(outbox, standin.client, clock=lambda: clock["now"])
        held = worker.run_once()
        row = outbox.rows()[0]
        early = worker.run_once()
        clock["now"] = now + timedelta(seconds=30)
        delivered = worker.run_once()
        observed = (
            f"held={held.retrying} state={row['status']} next={row['next_attempt_at']} "
            f"before_wait={early.processed} after_wait={delivered.synced} "
            f"patch_calls={standin.server.patch_calls}"
        )
        ok = (
            held.retrying == 1
            and row["status"] == RETRYING
            and row["next_attempt_at"] == "2026-11-24T12:00:30Z"
            and early.processed == 0
            and delivered.synced == 1
            and standin.server.patch_calls == 2
            and outbox.rows()[0]["status"] == SYNCED
        )
        return DrillResult("API limit exceeded", "PATCH 429 with Retry-After 30 seconds", observed, ok)
    finally:
        outbox.close()
        standin.close()


class Token:
    def __init__(self):
        self.value = "token-1"
        self.instance_url = "https://example.my.salesforce.com"


class DownAuth:
    def __init__(self, transport):
        self.transport = transport

    def get_access_token(self):
        return Token()


def drill_subscriber_down() -> DrillResult:
    now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
    store = StatusStore(":memory:", clock=_clock_at(now))
    try:
        store.apply_event(CHANNEL, StatusEvent(3, "INT-20261124-0001", "Lead", "New", "Inbound Sales"))

        def down(method, url, headers, body, timeout):
            raise NetworkError("connection refused")

        down_stats = StatusSubscriber(
            store,
            SalesforceEventSource(DownAuth(down)),
            object(),
        ).run_once()
        cursor_while_down = store.cursor(CHANNEL)
        error_while_down = store.last_error(CHANNEL)

        class Recovery:
            def take(self, channel, replay_from):
                self.replay_from = replay_from
                return [StatusEvent(4, "INT-20261124-0001", "Lead", "Working - Contacted", "Inbound Sales")]

        recovery = Recovery()
        back = StatusSubscriber(store, recovery, object()).run_once()
        observed = (
            f"deferred={down_stats.deferred} cursor_while_down={cursor_while_down} "
            f"error={error_while_down} resumed_from={recovery.replay_from} "
            f"applied={back.applied} status={store.get('INT-20261124-0001', 'Lead')['status']} "
            f"error_after={store.last_error(CHANNEL)}"
        )
        ok = (
            down_stats.deferred
            and down_stats.applied == 0
            and cursor_while_down == 3
            and error_while_down is not None
            and "connection refused" in error_while_down
            and recovery.replay_from == 3
            and back.applied == 1
            and store.get("INT-20261124-0001", "Lead")["status"] == "Working - Contacted"
            and store.last_error(CHANNEL) is None
        )
        return DrillResult("Subscriber down", "CometD connection refused, then one new event", observed, ok)
    finally:
        store.close()


def run_drills() -> list[DrillResult]:
    return [
        drill_wrong_secret(),
        drill_network_failure(),
        drill_validation_failure(),
        drill_duplicate_submission(),
        drill_api_limit(),
        drill_subscriber_down(),
    ]


class FaultDrillTests(unittest.TestCase):
    def test_each_fault_recovers_as_the_matrix_requires(self):
        results = run_drills()
        self.assertEqual([result.name for result in results], [
            "Wrong secret",
            "Network failure",
            "Validation failure",
            "Duplicate submission",
            "API limit exceeded",
            "Subscriber down",
        ])
        failed = [f"{result.name}: {result.observed}" for result in results if not result.ok]
        self.assertEqual(failed, [])

    def test_expired_token_refreshes_once(self):
        standin = StandIn()
        now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
        outbox = Outbox(":memory:", clock=_clock_at(now))
        try:
            standin.server.patch_script = [
                (401, {}, b'[{"message":"Session expired or invalid","errorCode":"INVALID_SESSION_ID"}]')
            ]
            outbox.accept_conversation(SAMPLE_CONVERSATIONS[0])
            stats = OutboxWorker(outbox, standin.client, clock=_clock_at(now)).run_once()
            self.assertEqual(stats.synced, 1)
            self.assertEqual(standin.server.token_calls, 2)
            self.assertEqual(standin.server.patch_calls, 2)
            self.assertEqual(outbox.rows()[0]["attempts"], 0)
            self.assertEqual(outbox.rows()[0]["status"], SYNCED)
            stored = standin.server.records[(SAMPLE_CONVERSATIONS[0]["expected"], SAMPLE_CONVERSATIONS[0]["intake_ref"])]
            self.assertNotIn("Status", stored)
            self.assertEqual(EXTERNAL_ID_FIELD, "Intake_Ref__c")
        finally:
            outbox.close()
            standin.close()

    def test_second_401_is_dead_letter(self):
        standin = StandIn()
        now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
        outbox = Outbox(":memory:", clock=_clock_at(now))
        try:
            standin.server.patch_script = [
                (401, {}, b'[{"message":"Session expired or invalid","errorCode":"INVALID_SESSION_ID"}]'),
                (401, {}, b'[{"message":"Session expired or invalid","errorCode":"INVALID_SESSION_ID"}]'),
            ]
            outbox.accept_conversation(SAMPLE_CONVERSATIONS[0])
            stats = OutboxWorker(outbox, standin.client, clock=_clock_at(now)).run_once()
            self.assertEqual(stats.dead_letter, 1)
            self.assertEqual(standin.server.token_calls, 2)
            self.assertEqual(standin.server.patch_calls, 2)
            self.assertEqual(outbox.rows()[0]["status"], DEAD_LETTER)
        finally:
            outbox.close()
            standin.close()


def main() -> None:
    for result in run_drills():
        mark = "pass" if result.ok else "fail"
        print(f"{mark}\t{result.name}\t{result.fault}\t{result.observed}")


if __name__ == "__main__":
    main()
