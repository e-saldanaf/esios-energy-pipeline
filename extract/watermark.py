"""Watermark logic: compute the extraction window per indicator.

DIDACTIC NOTE — Design for unreliable schedulers:
    GitHub Actions cron is best-effort (empirically ~40-50% hit rate on
    hourly schedules). Instead of assuming punctuality, every run derives
    its window from the data itself: [last loaded timestamp, now].
    Skipped runs become latency, never data loss. The same principle
    underpins Airflow's data-interval model — this is scheduler-agnostic
    engineering, not a GitHub workaround.
"""

from datetime import datetime, timedelta, timezone

from psycopg import Connection

from extract.config import settings
from extract.sql_loader import load_sql


def get_extraction_window(
    conn: Connection, indicator_id: int
) -> tuple[datetime, datetime]:
    """Return (start, end) UTC window for one indicator.

    - First run (no data): start = configured backfill start.
    - Normal run: start = watermark (inclusive on purpose: ESIOS revises
      recent values, and MERGE makes re-reading the boundary hour free).
    - Long outage: window capped at `max_window_days`; the next runs keep
      catching up chunk by chunk until current. Bounded self-healing.
    """
    sql = load_sql("queries/get_watermark.sql")
    with conn.cursor() as cur:
        cur.execute(sql, {"indicator_id": indicator_id})
        row = cur.fetchone()

    watermark: datetime | None = row[0] if row else None
    start = watermark or settings.default_backfill_start
    now = datetime.now(timezone.utc)
    end = min(start + timedelta(days=settings.max_window_days), now)
    return start, end
