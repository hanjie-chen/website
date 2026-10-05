"""Run an optional one-off brief retention cleanup."""

import argparse
import logging

import daily_briefs
from config import Daily_Briefs_Directory

LOGGER = logging.getLogger(__name__)


def main() -> None:
    argparse.ArgumentParser(description=__doc__).parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s brief_cleanup %(message)s"
    )
    LOGGER.info("removed=%d", daily_briefs.prune_briefs(Daily_Briefs_Directory))


if __name__ == "__main__":
    main()
