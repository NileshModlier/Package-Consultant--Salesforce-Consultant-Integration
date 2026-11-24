"""Point-in-time counts for the intake outbox and the status subscriber.

One call reads the current rows. It does not poll, alert, or restart a worker.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from integration.outbox import DEAD_LETTER, PENDING, RETRYING, SYNCED, Outbox
from integration.subscriber import CHANNEL, StatusStore


@dataclass(frozen=True)
class DeadLetterRow:
    intake_ref: str
    object_api_name: str
    attempts: int
    last_error: str


@dataclass(frozen=True)
class Dashboard:
    pending: int
    retrying: int
    synced: int
    dead_letter: int
    retry_attempts: int
    dead_letters: tuple[DeadLetterRow, ...]
    status_rows: int
    replay_cursor: int | None
    subscriber_error: str | None


def snapshot(outbox: Outbox, store: StatusStore | None = None, channel: str = CHANNEL) -> Dashboard:
    counts = outbox.counts()
    letters = tuple(
        DeadLetterRow(
            intake_ref=row["intake_ref"],
            object_api_name=row["object_api_name"],
            attempts=int(row["attempts"]),
            last_error=row["last_error"] or "",
        )
        for row in outbox.dead_letter_rows()
    )
    status_rows = 0
    cursor = None
    error = None
    if store is not None:
        status_rows = store.count()
        cursor = store.cursor(channel)
        error = store.last_error(channel)
    return Dashboard(
        pending=counts[PENDING],
        retrying=counts[RETRYING],
        synced=counts[SYNCED],
        dead_letter=counts[DEAD_LETTER],
        retry_attempts=outbox.retry_attempts(),
        dead_letters=letters,
        status_rows=status_rows,
        replay_cursor=cursor,
        subscriber_error=error,
    )


def format_dashboard(board: Dashboard) -> str:
    lines = [
        "Intake synchronization",
        f"Pending {board.pending}",
        f"Retrying {board.retrying}",
        f"Synced {board.synced}",
        f"Dead Letter {board.dead_letter}",
        f"Retry attempts {board.retry_attempts}",
        f"Status rows {board.status_rows}",
        f"Replay cursor {board.replay_cursor if board.replay_cursor is not None else 'none'}",
        f"Subscriber error {board.subscriber_error or 'none'}",
    ]
    if board.dead_letters:
        lines.append("Dead letters")
        for row in board.dead_letters:
            lines.append(
                f"  {row.intake_ref} {row.object_api_name} attempts={row.attempts} {row.last_error}"
            )
    return "\n".join(lines)


def main() -> None:
    outbox_path = os.environ.get("INTAKE_OUTBOX_PATH", "intake_outbox.sqlite")
    status_path = os.environ.get("INTAKE_STATUS_PATH", "intake_status.sqlite")
    outbox = Outbox(outbox_path)
    store = StatusStore(status_path) if os.path.exists(status_path) else None
    try:
        print(format_dashboard(snapshot(outbox, store)))
    finally:
        outbox.close()
        if store is not None:
            store.close()


if __name__ == "__main__":
    main()
