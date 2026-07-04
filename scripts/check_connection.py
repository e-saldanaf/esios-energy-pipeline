"""Connectivity smoke test: validates credentials, session pooler and
self-provisions the raw schema. Runnable BEFORE the ESIOS token arrives.

Usage (from project root):
    python -m scripts.check_connection

DIDACTIC NOTE — What each check proves:
    1. connect()        -> credentials + host + session pooler are correct
    2. version()        -> Postgres >= 15, i.e. MERGE is available
    3. DDL execution    -> the pipeline can self-provision its schema
    4. catalog query    -> the raw table actually exists afterwards
"""

import psycopg

from extract.main import build_conninfo
from extract.sql_loader import load_sql


def main() -> None:
    with psycopg.connect(build_conninfo()) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version()")
            version = cur.fetchone()[0].split(",")[0]
            print(f"Connected: {version}")

            major = int(version.split()[1].split(".")[0])
            assert major >= 15, f"Postgres {major} < 15: MERGE unavailable!"

            cur.execute(load_sql("ddl/create_raw_schema.sql"))
            conn.commit()

            cur.execute(
                "SELECT count(*) FROM information_schema.tables "
                "WHERE table_schema = 'raw' AND table_name = 'esios_indicator_values'"
            )
            assert cur.fetchone()[0] == 1, "raw table missing!"
            print("Schema 'raw' provisioned. Pipeline-ready.")


if __name__ == "__main__":
    main()