"""Pipeline entrypoint: extract each configured indicator and merge into raw.

Run locally:    python -m extract.main
Run in CI:      same command, secrets injected as env vars.

DIDACTIC NOTE — Failure isolation:
    One indicator failing must not poison the rest. Each indicator runs in
    its own try/except and its own transaction; the process exits non-zero
    if ANY failed so the CI run is correctly marked red, but healthy
    indicators still get their data. Partial success beats total failure.
"""

import sys

import psycopg

from extract.config import INDICATORS, settings
from extract.esios_client import EsiosClient
from extract.loader import merge_indicator_values, normalise_values
from extract.logging_setup import get_logger
from extract.sql_loader import load_sql
from extract.watermark import get_extraction_window

logger = get_logger("pipeline")


def build_conninfo() -> str:
    return (
        f"host={settings.db_host} port={settings.db_port} "
        f"dbname={settings.db_name} user={settings.db_user} "
        f"password={settings.db_password} sslmode=require"
    )


def run() -> int:
    client = EsiosClient()
    failures = 0

    with psycopg.connect(build_conninfo()) as conn:
        # Idempotent DDL: safe to run every time, self-provisioning on day 1.
        with conn.cursor() as cur:
            cur.execute(load_sql("ddl/create_raw_schema.sql"))
        conn.commit()

        for indicator_id, slug in INDICATORS.items():
            try:
                start, end = get_extraction_window(conn, indicator_id)
                values = client.get_indicator_values(indicator_id, start, end)
                rows = normalise_values(indicator_id, values)
                merged = merge_indicator_values(conn, rows)
                logger.info(
                    "indicator_done",
                    extra={"ctx": {"indicator": slug, "rows_merged": merged}},
                )
            except Exception:
                failures += 1
                logger.exception(
                    "indicator_failed", extra={"ctx": {"indicator": slug}}
                )

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
