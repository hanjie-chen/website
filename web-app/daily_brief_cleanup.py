"""Run brief retention once, or daily as the Compose maintenance service."""

import argparse
import logging
import signal
import time
from pathlib import Path
from threading import Event

import daily_briefs
from config import Daily_Briefs_Directory

LOGGER = logging.getLogger(__name__)
HEALTH_FILE = Path("/tmp/daily-brief-cleanup.ok")


def watch(directory, stop: Event) -> None:
    # Clear the previous process's marker so failed startup cannot look healthy.
    HEALTH_FILE.unlink(missing_ok=True)
    last_cleaned = None
    while not stop.is_set():
        today = daily_briefs._brief_today()
        if today != last_cleaned:
            removed = daily_briefs.prune_briefs(directory)
            HEALTH_FILE.touch()
            LOGGER.info("date=%s removed=%d", today, removed)
            last_cleaned = today
        # Check the local date rather than waiting 24 hours from startup. This
        # also handles clock corrections and allows prompt shutdown.
        stop.wait(60)


def healthy() -> bool:
    try:
        age = time.time() - HEALTH_FILE.stat().st_mtime
    except FileNotFoundError:
        return False
    return 0 <= age < 26 * 60 * 60


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--watch", action="store_true")
    mode.add_argument("--healthcheck", action="store_true")
    args = parser.parse_args()
    if args.healthcheck:
        raise SystemExit(0 if healthy() else 1)

    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s brief_cleanup %(message)s"
    )
    if args.watch:
        stop = Event()
        for signum in (signal.SIGTERM, signal.SIGINT):
            signal.signal(signum, lambda *_: stop.set())
        watch(Daily_Briefs_Directory, stop)
    else:
        LOGGER.info("removed=%d", daily_briefs.prune_briefs(Daily_Briefs_Directory))


if __name__ == "__main__":
    main()
