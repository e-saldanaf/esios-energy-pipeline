"""Extraction window logic.

DIDACTIC NOTE — Two modes, zero implicit state:

    AUTOMATIC (default, daily cron):
        start = today - 2 days (UTC midnight)
        end   = today (UTC midnight)

        Why D-2 and not D-1? The cron runs at ~07:23 GMT+1. At that time,
        D-1 data is complete and published by ESIOS. D-2 is included as a
        one-day overlap to capture ESIOS revisions: generation measured values
        are corrected days after initial publication. The MERGE's
        `IS DISTINCT FROM` branch picks up those corrections for free.

    MANUAL (backfill / re-extraction):
        Driven by EXTRACT_START and EXTRACT_END env vars (yyyy-mm-dd).
        Set them in the GitHub Actions workflow_dispatch inputs or locally:

            EXTRACT_START=2025-01-01 EXTRACT_END=2025-12-31 python -m extract.main

        No cap on the window size — single operator, knows what they're doing.
        Enterprise context would require chunking; that complexity is not
        justified here (see decisions log).

DIDACTIC NOTE — Why watermark is gone:
    The previous watermark design read max(datetime_utc) from the table to
    derive the next window. That created implicit state: the pipeline's
    behaviour depended on what was already in the DB. Explicit date parameters
    are simpler, more predictable, and easier to reason about in an interview.
    The table's `updated_at` column now answers "what changed recently?"
    without any watermark query.
"""

import os
from datetime import datetime, timedelta, timezone


def get_extraction_window() -> tuple[datetime, datetime]:
    """Return (start, end) UTC window for the current run.

    Reads EXTRACT_START / EXTRACT_END from environment.
    Falls back to automatic D-2 / D mode if not set.
    """
    raw_start = os.getenv("EXTRACT_START")
    raw_end   = os.getenv("EXTRACT_END")

    if raw_start and raw_end:
        # Manual mode: parse dates, set to UTC midnight
        start = datetime.strptime(raw_start, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        end   = datetime.strptime(raw_end,   "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
        return start, end

    # Automatic mode: D-2 to D (UTC midnight boundaries)
    today = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    return today - timedelta(days=2), today