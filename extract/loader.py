"""Loader: write raw API payloads into Supabase using the stage-then-MERGE pattern.

Flow per indicator, inside ONE transaction:
    1. CREATE TEMP TABLE ... ON COMMIT DROP    (staging zone)
    2. COPY rows into the temp table           (fast bulk load)
    3. MERGE temp -> raw.esios_indicator_values (idempotent write)
    4. COMMIT (temp table vanishes)

DIDACTIC NOTE — Why COPY instead of executemany:
    COPY is Postgres' bulk-ingestion protocol: one network round-trip,
    server-side parsing. executemany is a loop of INSERTs in disguise.
    At 24 rows/day the difference is invisible; at 24 million it is the
    difference between minutes and hours. Build the habit at toy scale.

DIDACTIC NOTE — Transactionality = atomicity:
    If MERGE fails, the transaction rolls back and raw stays untouched.
    A consumer can never observe a half-loaded window.
"""

from datetime import datetime, timezone
from typing import Any

from psycopg import Connection

from extract.logging_setup import get_logger
from extract.sql_loader import load_sql

logger = get_logger("loader")


def normalise_values(
    indicator_id: int, api_values: list[dict[str, Any]]
) -> list[tuple[int, datetime, int, float | None]]:
    """Map raw API objects to (indicator_id, datetime_utc, geo_id, value) tuples.

    Kept as a PURE function (no I/O) so it is trivially unit-testable with
    fixture payloads — see tests/test_loader.py.
    """
    rows = []
    for item in api_values:
        # ESIOS returns `datetime_utc`; fall back defensively to `datetime`.
        raw_ts = item.get("datetime_utc") or item["datetime"]
        ts = datetime.fromisoformat(raw_ts)
        if ts.tzinfo is None:  # never trust naive timestamps
            ts = ts.replace(tzinfo=timezone.utc)
        rows.append(
            (indicator_id, ts, item.get("geo_id") or 0, item.get("value"))
        )
    return rows


def merge_indicator_values(
    conn: Connection, rows: list[tuple[int, datetime, int, float | None]]
) -> int:
    """Stage rows and MERGE them into raw. Returns rows merged (staged count)."""
    if not rows:
        logger.info("merge_skipped_empty", extra={"ctx": {"rows": 0}})
        return 0

    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(load_sql("ddl/create_temp_staging.sql"))
            with cur.copy(
                "COPY tmp_indicator_values (indicator_id, datetime_utc, geo_id, value) FROM STDIN"
            ) as copy:
                for row in rows:
                    copy.write_row(row)
            cur.execute(load_sql("merge/merge_indicator_values.sql"))

    logger.info("merge_completed", extra={"ctx": {"rows": len(rows)}})
    return len(rows)
