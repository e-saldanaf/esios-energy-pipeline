"""Central configuration for the extraction layer.

DIDACTIC NOTE — Why pydantic-settings instead of os.environ:
    1. Fail-fast: the pipeline crashes at startup with a clear error if a
       required variable is missing, instead of failing mid-run with a
       cryptic `NoneType` error after already touching the database.
    2. Type coercion: env vars are always strings; pydantic converts and
       validates them (e.g. DB_PORT becomes an int).
    3. Single source of truth: every module imports `settings`, nobody
       reads os.environ directly. This is Clean Architecture's config layer.

    Exception: LOG_FORMAT and EXTRACT_START/EXTRACT_END are read with
    os.getenv directly. LOG_FORMAT is infrastructure config (display), not
    business config — importing settings in logging_setup would create a
    circular dependency. EXTRACT_START/EXTRACT_END are run-time overrides
    read inside watermark.py, not startup config.

Secrets are NEVER hardcoded here. Locally they come from `.env`
(git-ignored); in CI they are injected as GitHub Actions secrets.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # --- ESIOS API ---
    esios_api_token: str
    esios_base_url: str = "https://api.esios.ree.es"

    # --- Supabase (Postgres) ---
    # Use the SESSION pooler connection string (port 5432).
    # Transaction-mode pooling (port 6543) breaks temp tables, which our
    # MERGE staging pattern relies on. Knowing WHY is interview material.
    db_host: str
    db_port: int = 5432
    db_name: str = "postgres"
    db_user: str
    db_password: str


# DIDACTIC NOTE — Indicator registry:
# One generic raw table + this registry means adding a new source indicator
# (e.g. demand in phase 2) requires ZERO new DDL and ZERO new SQL.
#
# All ids verified against live ESIOS catalogue on 2026-07-22.
# geo_id filtering (Spain = 3) happens in dbt staging, not here.
INDICATORS: dict[int, str] = {
    # Hourly spot price — multi-geo (MIBEL + European market).
    # geo_id=3 (España) filtered in staging.
    600:   "spot_market_price",

    # National generation mix — 10-minute granularity, geo_id=3 (España) only.
    # Aggregated to hourly in dbt staging via date_trunc + sum/avg.
    2038:  "generation_wind",
    2040:  "generation_coal",
    2041:  "generation_combined_cycle",
    2042:  "generation_hydro",
    2044:  "generation_solar_pv",
    2051:  "generation_cogen_residues",
    10004: "generation_total",
}


settings = Settings()