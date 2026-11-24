"""Apply Intake_Status__e to the intake agent.

The subscriber stores the last replay id, ignores a replay id it has already
applied, and calls the Apex catch-up resource when Salesforce no longer has
that replay id. One run reads one batch. It does not poll on a timer.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Mapping
from urllib.parse import urlencode

from integration.sf_client import HttpResponse, NetworkError

CHANNEL = "/event/Intake_Status__e"
REPLAY_NEW = -1
REPLAY_ALL = -2


class ReplayExpired(Exception):
    """The stored replay id is outside the event retention window."""


class CatchUpError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class StatusEvent:
    replay_id: int
    intake_ref: str
    object_type: str
    status: str
    owner_name: str


@dataclass(frozen=True)
class StatusSnapshot:
    intake_ref: str
    object_type: str
    status: str
    owner_name: str


@dataclass
class SyncStats:
    applied: int = 0
    duplicates: int = 0
    caught_up: int = 0
    replay_expired: bool = False
    deferred: bool = False
    error: str | None = None


class StatusStore:
    """Latest status for each intake reference, plus the replay cursor."""

    def __init__(self, db_path: str = "intake_status.sqlite", clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS intake_status (
                intake_ref TEXT NOT NULL,
                object_type TEXT NOT NULL,
                status TEXT NOT NULL,
                owner_name TEXT NOT NULL,
                replay_id INTEGER,
                source TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (intake_ref, object_type)
            );
            CREATE TABLE IF NOT EXISTS replay_cursor (
                channel TEXT PRIMARY KEY,
                replay_id INTEGER,
                resume_new INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS seen_replay (
                channel TEXT NOT NULL,
                replay_id INTEGER NOT NULL,
                PRIMARY KEY (channel, replay_id)
            );
            CREATE TABLE IF NOT EXISTS sync_health (
                channel TEXT PRIMARY KEY,
                last_error TEXT,
                updated_at TEXT NOT NULL
            );
            """
        )
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def now(self) -> datetime:
        return self._clock()

    def replay_argument(self, channel: str) -> int:
        row = self._conn.execute(
            "SELECT replay_id, resume_new FROM replay_cursor WHERE channel = ?",
            (channel,),
        ).fetchone()
        if row is None or row["resume_new"]:
            return REPLAY_NEW
        if row["replay_id"] is None:
            return REPLAY_NEW
        return int(row["replay_id"])

    def seen(self, channel: str, replay_id: int) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM seen_replay WHERE channel = ? AND replay_id = ?",
            (channel, replay_id),
        ).fetchone()
        return row is not None

    def apply_event(self, channel: str, event: StatusEvent) -> bool:
        """Return True when the event is new. A repeated replay id is ignored."""
        if self.seen(channel, event.replay_id):
            return False
        now = _iso(self._clock())
        self._conn.execute(
            """
            INSERT INTO intake_status (
                intake_ref, object_type, status, owner_name, replay_id, source, updated_at
            ) VALUES (?, ?, ?, ?, ?, 'event', ?)
            ON CONFLICT(intake_ref, object_type) DO UPDATE SET
                status = excluded.status,
                owner_name = excluded.owner_name,
                replay_id = excluded.replay_id,
                source = 'event',
                updated_at = excluded.updated_at
            """,
            (event.intake_ref, event.object_type, event.status, event.owner_name, event.replay_id, now),
        )
        self._conn.execute(
            "INSERT INTO seen_replay (channel, replay_id) VALUES (?, ?)",
            (channel, event.replay_id),
        )
        self._conn.execute(
            """
            INSERT INTO replay_cursor (channel, replay_id, resume_new)
            VALUES (?, ?, 0)
            ON CONFLICT(channel) DO UPDATE SET replay_id = excluded.replay_id, resume_new = 0
            """,
            (channel, event.replay_id),
        )
        self._conn.commit()
        return True

    def mark_resume_new(self, channel: str) -> None:
        self._conn.execute(
            """
            INSERT INTO replay_cursor (channel, replay_id, resume_new)
            VALUES (?, NULL, 1)
            ON CONFLICT(channel) DO UPDATE SET resume_new = 1
            """,
            (channel,),
        )
        self._conn.commit()

    def apply_snapshot(self, snapshot: StatusSnapshot) -> None:
        now = _iso(self._clock())
        self._conn.execute(
            """
            INSERT INTO intake_status (
                intake_ref, object_type, status, owner_name, replay_id, source, updated_at
            ) VALUES (?, ?, ?, ?, NULL, 'catchup', ?)
            ON CONFLICT(intake_ref, object_type) DO UPDATE SET
                status = excluded.status,
                owner_name = excluded.owner_name,
                source = 'catchup',
                updated_at = excluded.updated_at
            """,
            (snapshot.intake_ref, snapshot.object_type, snapshot.status, snapshot.owner_name, now),
        )
        self._conn.commit()

    def known_refs(self) -> list[str]:
        rows = self._conn.execute("SELECT DISTINCT intake_ref FROM intake_status ORDER BY intake_ref")
        return [row["intake_ref"] for row in rows]

    def get(self, intake_ref: str, object_type: str) -> sqlite3.Row | None:
        return self._conn.execute(
            "SELECT * FROM intake_status WHERE intake_ref = ? AND object_type = ?",
            (intake_ref, object_type),
        ).fetchone()

    def count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS n FROM intake_status").fetchone()
        return int(row["n"])

    def cursor(self, channel: str) -> int | None:
        row = self._conn.execute(
            "SELECT replay_id FROM replay_cursor WHERE channel = ?",
            (channel,),
        ).fetchone()
        if row is None or row["replay_id"] is None:
            return None
        return int(row["replay_id"])

    def note_failure(self, channel: str, message: str) -> None:
        now = _iso(self._clock())
        self._conn.execute(
            """
            INSERT INTO sync_health (channel, last_error, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(channel) DO UPDATE SET
                last_error = excluded.last_error,
                updated_at = excluded.updated_at
            """,
            (channel, message[:1000], now),
        )
        self._conn.commit()

    def clear_failure(self, channel: str) -> None:
        self._conn.execute("DELETE FROM sync_health WHERE channel = ?", (channel,))
        self._conn.commit()

    def last_error(self, channel: str) -> str | None:
        row = self._conn.execute(
            "SELECT last_error FROM sync_health WHERE channel = ?",
            (channel,),
        ).fetchone()
        if row is None or row["last_error"] is None:
            return None
        return str(row["last_error"])


class StatusSubscriber:
    def __init__(self, store: StatusStore, source: object, catchup: object, channel: str = CHANNEL) -> None:
        self._store = store
        self._source = source
        self._catchup = catchup
        self._channel = channel

    def run_once(self) -> SyncStats:
        stats = SyncStats()
        replay_from = self._store.replay_argument(self._channel)
        try:
            events = list(self._source.take(self._channel, replay_from))
        except ReplayExpired:
            stats.replay_expired = True
            try:
                stats.caught_up = self._catch_up()
            except (CatchUpError, NetworkError) as error:
                return self._defer(stats, error)
            self._store.mark_resume_new(self._channel)
            try:
                events = list(self._source.take(self._channel, REPLAY_NEW))
            except ReplayExpired:
                events = []
            except (CatchUpError, NetworkError) as error:
                return self._defer(stats, error)
        except (CatchUpError, NetworkError) as error:
            return self._defer(stats, error)
        self._store.clear_failure(self._channel)
        self._apply(events, stats)
        return stats

    def _defer(self, stats: SyncStats, error: Exception) -> SyncStats:
        stats.deferred = True
        stats.error = str(error)
        self._store.note_failure(self._channel, str(error))
        return stats

    def _apply(self, events: list[StatusEvent], stats: SyncStats) -> None:
        for event in events:
            if self._store.apply_event(self._channel, event):
                stats.applied += 1
            else:
                stats.duplicates += 1

    def _catch_up(self) -> int:
        refs = self._store.known_refs()
        since = None if refs else self._store.now() - timedelta(hours=24)
        snapshots = list(self._catchup.fetch(since=since, refs=refs or None))
        for snapshot in snapshots:
            self._store.apply_snapshot(snapshot)
        return len(snapshots)


class SalesforceCatchUp:
    """GET /services/apexrest/intake/status for missed-event recovery."""

    def __init__(self, auth: object, timeout: float = 30) -> None:
        self._auth = auth
        self._timeout = timeout

    def fetch(self, since: datetime | None = None, refs: list[str] | None = None) -> list[StatusSnapshot]:
        token = self._auth.get_access_token()
        params = {}
        if since is not None:
            params["since"] = since.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        if refs:
            params["refs"] = ",".join(refs)
        url = f"{token.instance_url}/services/apexrest/intake/status?{urlencode(params)}"
        try:
            response = self._auth.transport(
                "GET",
                url,
                {"Authorization": f"Bearer {token.value}", "Accept": "application/json"},
                None,
                self._timeout,
            )
        except NetworkError as error:
            raise CatchUpError(str(error)) from error
        if response.status in (408, 429) or 500 <= response.status <= 599:
            raise CatchUpError(f"Catch-up failed with HTTP {response.status}", status_code=response.status)
        if response.status != 200:
            raise CatchUpError(_body_text(response), status_code=response.status)
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CatchUpError("Catch-up response was not JSON") from error
        if not isinstance(payload, list):
            raise CatchUpError("Catch-up response was not a list")
        return [_snapshot(row) for row in payload]


class SalesforceEventSource:
    """One CometD handshake, subscribe, and connect cycle for Intake_Status__e."""

    def __init__(self, auth: object, api_version: str = "62.0", timeout: float = 30) -> None:
        self._auth = auth
        self._api_version = api_version
        self._timeout = timeout

    def take(self, channel: str, replay_from: int) -> list[StatusEvent]:
        token = self._auth.get_access_token()
        url = f"{token.instance_url}/cometd/{self._api_version}"
        headers = {
            "Authorization": f"Bearer {token.value}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        handshake = self._post(
            url,
            headers,
            [
                {
                    "channel": "/meta/handshake",
                    "version": "1.0",
                    "minimumVersion": "1.0",
                    "supportedConnectionTypes": ["long-polling"],
                }
            ],
        )
        client_id = _advice_value(handshake, "/meta/handshake", "clientId")
        if not client_id:
            raise CatchUpError("Streaming handshake did not return a client id")
        subscribed = self._post(
            url,
            headers,
            [
                {
                    "channel": "/meta/subscribe",
                    "clientId": client_id,
                    "subscription": channel,
                    "ext": {"replay": {channel: replay_from}},
                }
            ],
        )
        if _replay_rejected(subscribed):
            self._disconnect(url, headers, client_id)
            raise ReplayExpired(f"Replay id {replay_from} is no longer available")
        delivered = self._post(
            url,
            headers,
            [{"channel": "/meta/connect", "clientId": client_id, "connectionType": "long-polling"}],
        )
        self._disconnect(url, headers, client_id)
        return [event for event in (_parse_event(message, channel) for message in delivered) if event is not None]

    def _disconnect(self, url: str, headers: Mapping[str, str], client_id: str) -> None:
        try:
            self._post(url, headers, [{"channel": "/meta/disconnect", "clientId": client_id}])
        except (CatchUpError, ReplayExpired):
            return

    def _post(self, url: str, headers: Mapping[str, str], messages: list[dict]) -> list[dict]:
        try:
            response = self._auth.transport("POST", url, headers, json.dumps(messages).encode("utf-8"), self._timeout)
        except NetworkError as error:
            raise CatchUpError(str(error)) from error
        if response.status in (408, 429) or 500 <= response.status <= 599:
            raise CatchUpError(f"Streaming call failed with HTTP {response.status}", status_code=response.status)
        if response.status != 200:
            raise CatchUpError(_body_text(response), status_code=response.status)
        try:
            payload = json.loads(response.body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise CatchUpError("Streaming response was not JSON") from error
        if not isinstance(payload, list):
            raise CatchUpError("Streaming response was not a Bayeux batch")
        return payload


def _advice_value(messages: list[dict], channel: str, field: str) -> str | None:
    for message in messages:
        if message.get("channel") == channel and message.get("successful") is True:
            value = message.get(field)
            if value:
                return str(value)
    return None


def _replay_rejected(messages: list[dict]) -> bool:
    for message in messages:
        if message.get("channel") != "/meta/subscribe" or message.get("successful") is not False:
            continue
        error = str(message.get("error", "")).lower()
        if "replay" in error:
            return True
    return False


def _parse_event(message: dict, channel: str) -> StatusEvent | None:
    if message.get("channel") != channel:
        return None
    data = message.get("data") or {}
    payload = data.get("payload") if isinstance(data, dict) else None
    if not isinstance(payload, dict):
        payload = data if isinstance(data, dict) else {}
    event_meta = data.get("event") if isinstance(data, dict) else None
    replay_id = None
    if isinstance(event_meta, dict):
        replay_id = event_meta.get("replayId")
    if replay_id is None:
        replay_map = (message.get("ext") or {}).get("replay") or {}
        replay_id = replay_map.get(channel)
    if replay_id is None:
        return None
    return StatusEvent(
        replay_id=int(replay_id),
        intake_ref=str(payload.get("Intake_Ref__c") or ""),
        object_type=str(payload.get("Object_Type__c") or ""),
        status=str(payload.get("Status__c") or ""),
        owner_name=str(payload.get("Owner_Name__c") or ""),
    )


def _snapshot(row: Mapping[str, object]) -> StatusSnapshot:
    return StatusSnapshot(
        intake_ref=str(row.get("intakeRef") or ""),
        object_type=str(row.get("objectType") or ""),
        status=str(row.get("status") or ""),
        owner_name=str(row.get("ownerName") or ""),
    )


def _body_text(response: HttpResponse) -> str:
    text = response.body.decode("utf-8", errors="replace").strip()
    return text or f"HTTP {response.status}"


def _iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
