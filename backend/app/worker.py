"""Background worker that drains the notification outbox."""

from __future__ import annotations

import argparse
import signal
import time

import app.models  # noqa: F401 - register ORM models with SQLAlchemy
from app.core.db import SessionLocal
from app.modules.notifications.service import process_pending
from app.modules.notifications.transport import SmtpTransport


def run_once(limit: int = 10) -> int:
    """Process one batch of due notifications and return the count."""
    with SessionLocal() as db:
        return process_pending(db, SmtpTransport(), limit=limit)


def run_forever(limit: int = 10, sleep_seconds: int = 5) -> None:
    """Continuously process due notifications until interrupted."""
    stop = False

    def handle_signal(_signum: int, _frame: object) -> None:
        nonlocal stop
        stop = True

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    while not stop:
        try:
            processed = run_once(limit=limit)
        except Exception:
            processed = 0
        if processed == 0:
            time.sleep(sleep_seconds)


def main() -> None:
    parser = argparse.ArgumentParser(description="Drain the notification outbox.")
    parser.add_argument("--once", action="store_true", help="Process one batch and exit.")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--sleep", type=int, default=5)
    args = parser.parse_args()

    if args.once:
        count = run_once(limit=args.limit)
        print(f"Processed {count} notification(s).")
    else:
        run_forever(limit=args.limit, sleep_seconds=args.sleep)


if __name__ == "__main__":
    main()
