"""Central configuration for the extraction layer.

DIDACTIC NOTE — Why pydantic-settings instead of os.environ:
    1. Fail-fast: the pipeline crashes at startup with a clear error if a
       required variable is missing, instead of failing mid-run with a
       cryptic `NoneType` error after already touching the database.
    2. Type coercion: env vars are always strings; pydantic converts and
       validates them (e.g. DB_PORT becomes an int).
    3. Single source of truth: every module imports `settings`, nobody
       reads os.environ directly. This is Clean Architecture's config layer.

Secrets are NEVER hardcoded here. Locally they come from `.env`
(git-ignored); in CI they are injected as GitHub Actions secrets.
"""

from datetime import datetime, timezone

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

    # --- Pipeline behaviour ---
    # First-run backfill start. Keep it modest: didactic project, not a
    # historical archive. Extend later if the dashboard needs more history.
    default_backfill_start: datetime = datetime(2026, 1, 1, tzinfo=timezone.utc)

    # Safety cap per run (days). If the watermark is very old (long outage),
    # we extract in bounded chunks instead of one giant request that could
    # hit API limits or blow memory. Self-healing, but politely.
    max_window_days: int = 31
    
    # Logging format: 'text' for local dev (coloured), 'json' for CI/production.
    # Set LOG_FORMAT=json in GitHub Actions env; leave as default locally.
    log_format: str = "text"

# DIDACTIC NOTE — Indicator registry:
# One generic raw table + this registry means adding a new source indicator
# (e.g. demand in phase 2) requires ZERO new DDL and ZERO new SQL.
# That extensibility claim will become a LinkedIn post when phase 2 lands.
#
# indicator_id -> human-readable slug (used only for logging/docs).
# 600 = Precio mercado SPOT diario (confirmed).
# Generation-by-technology ids: verify them against the live catalogue
# using `EsiosClient.list_indicators()` before enabling them.

INDICATORS: dict[int, str] = {
    # Hourly spot price — multi-geo (MIBEL + European market).
    # geo_id=3 (España) filtered in staging.
    600:   "spot_market_price",

    # National generation mix — 10-minute granularity, geo_id=3 (España) only.
    # Aggregated to hourly in dbt staging via date_trunc + sum/avg.
    # All verified against live catalogue on 2026-07-22.
    2038:  "generation_wind",
    2040:  "generation_coal",
    2041:  "generation_combined_cycle",
    2042:  "generation_hydro",
    2044:  "generation_solar_pv",
    2051:  "generation_cogen_residues",
    10004: "generation_total",
}


settings = Settings()
