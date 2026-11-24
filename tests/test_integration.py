"""Client credentials, PATCH upsert, and outbox retries against a local Salesforce stand-in."""

from __future__ import annotations

import json
import threading
import unittest
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import URLError
from urllib.parse import parse_qs, unquote

from integration.outbox import SYNCED, Outbox, OutboxWorker
from integration.sf_auth import SalesforceAuth, urllib_transport
from integration.sf_client import (
    EXTERNAL_ID_FIELD,
    HttpResponse,
    NetworkError,
    RetryableSalesforceError,
    SalesforceClient,
)
from tests.sample_conversations import SAMPLE_CONVERSATIONS


class SalesforceStandIn(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length).decode("utf-8")
        form = parse_qs(body)
        self.server.token_calls += 1
        self.server.grants.append(form.get("grant_type", [None])[0])
        self.server.client_ids.append(form.get("client_id", [None])[0])
        if "client_secret" not in form or form.get("grant_type", [None])[0] != "client_credentials":
            self._send(400, b'{"error":"invalid_grant"}')
            return
        port = self.server.server_address[1]
        payload = json.dumps(
            {
                "access_token": "test-access-token",
                "instance_url": f"http://127.0.0.1:{port}",
                "token_type": "Bearer",
                "expires_in": 3600,
            }
        ).encode("utf-8")
        self._send(200, payload)

    def do_PATCH(self):
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        self.server.authorizations.append(self.headers.get("Authorization"))
        if self.server.fail_queue:
            code = self.server.fail_queue.pop(0)
            headers = {"Retry-After": "0"} if code == 429 else {}
            message = json.dumps([{"message": "temporary", "errorCode": "SERVER_UNAVAILABLE"}]).encode()
            self.server.statuses.append(code)
            self._send(code, message, headers)
            return
        parts = [unquote(part) for part in self.path.split("/")]
        sobject = parts[5]
        external_field = parts[6]
        external_id = parts[7]
        if external_field != EXTERNAL_ID_FIELD:
            self._send(400, b'[{"message":"wrong external id","errorCode":"INVALID_FIELD"}]')
            return
        key = (sobject, external_id)
        created = key not in self.server.records
        self.server.records[key] = json.loads(raw.decode("utf-8"))
        self.server.statuses.append(201 if created else 204)
        self._send(201 if created else 204, b"")

    def _send(self, status, body, extra_headers=None):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), SalesforceStandIn)
        self.server.records = {}
        self.server.token_calls = 0
        self.server.grants = []
        self.server.client_ids = []
        self.server.authorizations = []
        self.server.statuses = []
        self.server.fail_queue = []
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        port = self.server.server_address[1]
        self.auth = SalesforceAuth(
            "intake-client",
            "intake-secret",
            f"http://127.0.0.1:{port}/services/oauth2/token",
            transport=urllib_transport,
        )
        self.client = SalesforceClient(self.auth, api_version="62.0")
        self.now = datetime(2026, 11, 24, 12, 0, tzinfo=timezone.utc)
        self.outbox = Outbox(":memory:", clock=lambda: self.now)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.outbox.close()

    def test_oauth_and_twenty_conversations_replay_to_one_record_each(self):
        worker = OutboxWorker(self.outbox, self.client, clock=lambda: self.now)
        for conversation in SAMPLE_CONVERSATIONS:
            self.outbox.accept_conversation(conversation)
        worker.run_until_idle()
        for conversation in SAMPLE_CONVERSATIONS:
            self.outbox.accept_conversation(conversation)
        replay = worker.run_until_idle()

        self.assertEqual(replay.processed, 0)
        self.assertEqual(self.server.token_calls, 1)
        self.assertEqual(self.server.grants, ["client_credentials"])
        self.assertEqual(self.server.client_ids, ["intake-client"])
        self.assertEqual(set(self.server.authorizations), {"Bearer test-access-token"})
        self.assertEqual(len(self.server.records), 20)
        self.assertEqual(self.outbox.counts()[SYNCED], 20)
        for conversation in SAMPLE_CONVERSATIONS:
            key = (conversation["expected"], conversation["intake_ref"])
            self.assertIn(key, self.server.records)
            self.assertNotIn("Status", self.server.records[key])
        self.assertEqual(self.server.statuses.count(201), 20)
        self.assertNotIn(204, self.server.statuses)

    def test_retry_408_429_and_5xx_then_one_upsert(self):
        conversation = SAMPLE_CONVERSATIONS[11]
        self.outbox.accept_conversation(conversation)
        self.server.fail_queue = [408, 429, 503]
        worker = OutboxWorker(
            self.outbox,
            self.client,
            clock=lambda: self.now,
            backoff=lambda attempts, retry_after: 0,
        )
        stats = worker.run_until_idle()
        self.assertEqual(stats.synced, 1)
        self.assertEqual(stats.dead_letter, 0)
        self.assertEqual(list(self.server.records), [("Case", conversation["intake_ref"])])
        self.assertEqual(self.server.statuses[:3], [408, 429, 503])
        self.assertEqual(self.server.statuses[-1], 201)
        stored = self.server.records[("Case", conversation["intake_ref"])]
        self.assertEqual(stored["Priority"], "High")
        self.assertEqual(self.outbox.rows()[0]["status"], SYNCED)

    def test_client_classifies_retryable_and_network_failures(self):
        token = json.dumps(
            {
                "access_token": "token",
                "instance_url": "https://example.my.salesforce.com",
                "expires_in": 3600,
            }
        ).encode()

        def scripted(status):
            calls = {"n": 0}

            def transport(method, url, headers, body, timeout):
                calls["n"] += 1
                if method == "POST":
                    return HttpResponse(200, {}, token)
                if status == "network":
                    raise URLError("timed out")
                headers_out = {"retry-after": "12"} if status == 429 else {}
                return HttpResponse(status, headers_out, b'[{"message":"no","errorCode":"UNAVAILABLE"}]')

            return transport

        for status in (408, 429, 500, 599, "network"):
            auth = SalesforceAuth("client", "secret", "https://example/token", scripted(status))
            client = SalesforceClient(auth)
            with self.assertRaises(RetryableSalesforceError) as caught:
                client.upsert("Case", "INT-20261124-0012", {"Subject": "Down"})
            if status == 429:
                self.assertEqual(caught.exception.retry_after, 12)
            if status == "network":
                self.assertIsInstance(caught.exception, NetworkError)


if __name__ == "__main__":
    unittest.main()
