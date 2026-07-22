# ESIOS Energy Pipeline

End-to-end analytics engineering project on the Spanish electricity market
(ESIOS/REE public API). **dbt Core is the star**; everything else exists to
feed it and show its output. Total infrastructure cost: **0 €**.

```
cron-job.org ──▶ workflow_dispatch ──▶ GitHub Actions
                                          │
                    Python extract (explicit date window, ESIOS API)
                                          ▼
                          Supabase (Postgres 17, schema raw)
                                          ▼
                     dbt Core (staging ▸ intermediate ▸ marts)
                          ├── tests + snapshots
                          ├── dbt docs ──▶ GitHub Pages
                          ▼
                     Evidence.dev static dashboard
```

## Project status

| Phase | Status |
|---|---|
| 1. Extract layer (explicit window + MERGE + SQL directory) | ✅ Complete |
| 2. CI/CD (Actions + secrets + keepalive + manual backfill inputs) | ✅ Complete |
| 3. dbt layer (models, tests, snapshots, docs) | 🔜 Next |
| 4. Evidence.dev dashboard | 🔜 Pending |
| 5. Demand indicator + weather correlation | 🗺️ Roadmap |

## Architecture

### Extract layer

The pipeline runs daily via GitHub Actions, triggered by cron-job.org through
`workflow_dispatch` (primary) with a native `schedule` as best-effort fallback.

Two extraction modes:

**Automatic (daily cron):** loads D-2 to today. D-2 overlap captures ESIOS
value revisions published days after the initial release. The `MERGE`'s
`IS DISTINCT FROM` branch picks up corrections for free.

**Manual (backfill):** driven by `EXTRACT_START` / `EXTRACT_END` env vars
(`yyyy-mm-dd`, inclusive end). Set them in the GitHub Actions
`workflow_dispatch` form or locally via `launch.json`. No window cap —
single operator project.

```bash
# Local manual backfill
EXTRACT_START=2025-01-01 EXTRACT_END=2025-12-31 python -m extract.main
```

### Raw schema

One generic long-format table (`raw.esios_indicator_values`) for all
indicators. Adding a new indicator requires zero DDL — one config line in
`extract/config.py`. Schema is self-provisioned on first run (idempotent DDL).

| Column | Type | Notes |
|---|---|---|
| `indicator_id` | integer | ESIOS indicator id |
| `datetime_utc` | timestamptz | Always stored in UTC |
| `geo_id` | integer | Geography (3 = España) |
| `value` | numeric | Nullable — ESIOS can publish nulls |
| `extracted_at` | timestamptz | First load timestamp |
| `updated_at` | timestamptz | Last MERGE update |

Primary key: `(indicator_id, datetime_utc, geo_id)` — guarantees idempotency.

### Indicators

| ID | Slug | Granularity | Geo scope |
|---|---|---|---|
| 600 | `spot_market_price` | Hourly | 6 countries (filtered to Spain in staging) |
| 2038 | `generation_wind` | 10-min | Spain only |
| 2040 | `generation_coal` | 10-min | Spain only |
| 2041 | `generation_combined_cycle` | 10-min | Spain only |
| 2042 | `generation_hydro` | 10-min | Spain only |
| 2044 | `generation_solar_pv` | 10-min | Spain only |
| 2051 | `generation_cogen_residues` | 10-min | Spain only |
| 10004 | `generation_total` | 10-min | Spain only |

All IDs verified against the live ESIOS catalogue on 2026-07-22.

## Decisions log

Deliberate architecture decisions, with the trade-off each one accepts.
This section is the project's real interview deliverable.

| Decision | Alternative rejected | Why |
|---|---|---|
| **No Airflow** | Airflow (daily driver at work) | A single daily batch with no cross-DAG dependencies doesn't justify an orchestrator's operational cost. Choosing NOT to use a tool you know is an architecture decision too. |
| **cron-job.org → `workflow_dispatch`** | GitHub `schedule` alone | Measured evidence: hourly `schedule` crons achieved ~42% hit rate on this account. Dispatch via REST API starts in seconds. Native cron kept as fallback. |
| **Explicit date window (D-2/D)** | Watermark-based extraction | Watermark creates implicit state: pipeline behaviour depends on what is already in the DB. Explicit parameters are simpler, more predictable, and easier to reason about. The `updated_at` column answers "what changed recently?" without any watermark query. D-2 overlap captures ESIOS revisions for free via `IS DISTINCT FROM`. |
| **Inclusive end date UX** | Exclusive end (API convention) | Users think in calendar dates. `EXTRACT_END=2026-01-31` should load January 31st, not stop before it. The code adds one day internally — the API boundary is an implementation detail, not a user concern. |
| **Postgres (Supabase) as warehouse** | MotherDuck / columnar DWH | At ~10² rows/day, columnar storage buys nothing. Free tier, most mature dbt adapter, native Evidence connection. I know exactly at which volume this decision stops scaling — and I'd move to Redshift, which I run in production. |
| **Session pooler (port 5432)** | Direct connection / transaction pooler | Direct connection is IPv6-only → CI runners fail. Transaction pooler destroys temp tables between statements → MERGE pattern breaks. Session pooler is the only option that satisfies both constraints simultaneously. |
| **`MERGE` (SQL:2003)** | `INSERT ... ON CONFLICT` | ANSI standard → transferable to Redshift/Snowflake/BigQuery. Conditional `WHEN MATCHED AND ... IS DISTINCT FROM` writes only real changes. ESIOS revises published values — this is a real business case, not defensive boilerplate. Concurrency caveat owned: not race-proof under concurrent writers — we have exactly one. |
| **`IF NOT EXISTS` + `TRUNCATE` on temp table** | `DROP / CREATE` per indicator | DDL inside a transaction can cause implicit commits. `IF NOT EXISTS` guarantees existence; `TRUNCATE` guarantees cleanliness between indicators in the same connection. Discovered and fixed on first production run. |
| **SQL in `.sql` files** | SQL strings inside Python | Reviewable diffs, sqlfluff-lintable, IDE syntax highlighting. Python orchestrates; SQL declares. dbt's philosophy applied to the extract layer. |
| **One generic raw table (long format)** | One table per indicator | Adding an indicator = one config line, zero DDL. Pivoting to wide format belongs to dbt staging, not ingestion. |
| **10-minute raw granularity, hourly in staging** | Hourly-only ingestion | ESIOS national generation indicators are natively 10-minute. No hourly national aggregate exists. Raw preserves source fidelity; `date_trunc + sum` in dbt staging produces the hourly grain. Transformation belongs to the transform layer. |
| **geo_id=3 filter in staging, not in extract** | Filter at API request time | The extract layer has no opinion on business logic. Filtering by geography is a transformation decision — documented, tested, and version-controlled alongside the model that uses it. |
| **Dedicated Supabase project** | Shared project with mobility-zgz | Blast radius isolation: a runaway backfill in one project cannot put the other in read-only mode. Credential rotation is independent. Free tier allows 2 active projects. |
| **Pipeline as Supabase keepalive** | Separate ping mechanism | Supabase pauses free projects after 7 days without connections. The daily pipeline generates a connection every run, keeping the project active organically. Verified empirically on first run attempt. |
| **No cap on manual extraction window** | `max_window_days` safety cap | Single operator (personal portfolio). The operator knows what they're doing when setting `EXTRACT_START`/`EXTRACT_END`. Enterprise context would require chunking and validation; that complexity is not justified here. |
| **Dual log formatter (text/json)** | JSON-only logging | JSON logs are for machines. `LOG_FORMAT=text` (default locally) gives coloured human-readable output in the VS Code terminal. `LOG_FORMAT=json` (set at CI job level) feeds structured logs to GitHub Actions. `os.getenv` used directly — importing `settings` here would create a circular dependency at module load time. |
| **`DBT_ENABLED` feature flag** | Deploy dbt steps immediately | dbt project doesn't exist yet. The flag lets the pipeline run green in CI today and activates the full path when dbt lands — no YAML rewrite, no red runs in between. Progressive delivery applied to a data pipeline. |

## Setup

### Prerequisites

- Python 3.12+
- conda environment with `pip install -r requirements.txt`
- Free ESIOS token: email `consultasios@ree.es`
- Supabase project (free tier, Postgres 17)

### Local setup

```bash
cp .env.example .env
# Fill in ESIOS_API_TOKEN and Supabase session-pooler credentials (port 5432)

pip install -r requirements.txt
pytest tests/ -q                    # 5 tests, should be green
python -m scripts.check_connection  # validates DB + provisions raw schema
python -m extract.main              # automatic mode: loads D-2 to today
```

### VS Code launch configurations (`.vscode/launch.json`)

Three configurations available in Run & Debug (`Ctrl+Shift+D`):

| Configuration | Mode | Env vars |
|---|---|---|
| Extract: automatic | D-2 to today | none |
| Extract: manual backfill | Custom date range | `EXTRACT_START`, `EXTRACT_END` |
| Check connection | Smoke test | none |

### GitHub Actions setup

See `docs/SETUP_CICD.md` for the complete one-time checklist:
secrets, fine-grained PAT, cron-job.org job, and GitHub Pages configuration.

## Env vars

| Variable | Required | Purpose |
|---|---|---|
| `ESIOS_API_TOKEN` | ✅ | Personal API token issued by REE |
| `DB_HOST` | ✅ | Supabase session-pooler host |
| `DB_PORT` | default 5432 | Postgres port — must be 5432 (session mode) |
| `DB_NAME` | default postgres | Database name |
| `DB_USER` | ✅ | `postgres.<project-ref>` |
| `DB_PASSWORD` | ✅ | Supabase database password |
| `EXTRACT_START` | optional | Manual backfill start (`yyyy-mm-dd`, inclusive) |
| `EXTRACT_END` | optional | Manual backfill end (`yyyy-mm-dd`, inclusive) |
| `LOG_FORMAT` | default text | `text` (local) or `json` (CI) |

## Repository structure

```
esios-energy-pipeline/
├── .github/workflows/daily_pipeline.yml   # CI/CD: extract + dbt (gated) + keepalive
├── docs/SETUP_CICD.md                     # One-time CI/CD setup checklist
├── extract/
│   ├── config.py                          # pydantic-settings + indicator registry
│   ├── esios_client.py                    # API client with retry + timeout
│   ├── loader.py                          # stage-then-MERGE pattern
│   ├── logging_setup.py                   # dual formatter (text/json)
│   ├── main.py                            # pipeline entrypoint
│   ├── sql_loader.py                      # loads .sql files with lru_cache
│   ├── watermark.py                       # explicit date window logic
│   └── sql/
│       ├── ddl/create_raw_schema.sql      # idempotent raw schema + table
│       ├── ddl/create_temp_staging.sql    # IF NOT EXISTS + TRUNCATE pattern
│       └── merge/merge_indicator_values.sql  # ANSI MERGE with IS DISTINCT FROM
├── dbt/                                   # 🔜 phase 3
├── evidence/                              # 🔜 phase 4
├── scripts/
│   ├── check_connection.py                # connectivity smoke test
│   └── discover_indicators.py             # ESIOS catalogue browser
├── tests/
│   └── test_loader.py                     # unit tests for normalise_values
├── .env.example
├── README.md
└── requirements.txt
```