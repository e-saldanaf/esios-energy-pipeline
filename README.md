# ESIOS Energy Pipeline

End-to-end analytics engineering project on the Spanish electricity market
(ESIOS/REE public API). **dbt Core is the star**; everything else exists to
feed it and show its output. Total infrastructure cost: **0 €**.

```
cron-job.org ──▶ workflow_dispatch ──▶ GitHub Actions
                                          │
                    Python extract (watermark, ESIOS API)
                                          ▼
                          Supabase (Postgres, schema raw)
                                          ▼
                     dbt Core (staging ▸ intermediate ▸ marts)
                          ├── tests + snapshots
                          ├── dbt docs ──▶ GitHub Pages
                          ▼
                     Evidence.dev dashboard
```

## Project status

| Phase | Status |
|---|---|
| 1. Extract layer (watermark + MERGE) | ✅ scaffolded |
| 2. CI/CD (Actions + cron-job.org + secrets) | 🔜 |
| 3. dbt layer (models, tests, snapshots, docs) | 🔜 |
| 4. Evidence.dev dashboard | 🔜 |
| 5. Demand indicator + weather correlation | 🗺️ roadmap |

## Decisions log

Deliberate architecture decisions, with the trade-off each one accepts.
This section is the project's real deliverable.

| Decision | Alternative rejected | Why |
|---|---|---|
| **No Airflow** | Airflow (my daily driver at work) | A single daily batch with no cross-DAG dependencies doesn't justify an orchestrator's operational cost. Choosing NOT to use a tool you know is an architecture decision too. |
| **cron-job.org → `workflow_dispatch`** | GitHub `schedule` alone | Measured evidence: hourly `schedule` crons achieved ~42% hit rate on this account. Dispatch via REST API starts in seconds. Native cron kept as fallback. |
| **Watermark extraction** | Fixed time-window extraction | Fixed windows turn scheduler skips into permanent data holes. Watermark makes the pipeline self-healing: skips become latency, never loss. |
| **Postgres (Supabase) as warehouse** | MotherDuck / columnar DWH | At ~10² rows/day, columnar storage buys nothing. Free tier, most mature dbt adapter, native Evidence connection. I know exactly at which volume this decision stops scaling — and I'd move to Redshift, which I run in production. |
| **`MERGE` (SQL:2003)** | `INSERT ... ON CONFLICT` | ANSI standard → transferable to Redshift/Snowflake/BigQuery. Conditional `WHEN MATCHED AND ... IS DISTINCT FROM` branch writes only real changes (ESIOS revises published values). Caveat owned: MERGE isn't race-proof under concurrent writers — we have exactly one. |
| **SQL in `.sql` files** | SQL strings inside Python | Reviewable diffs, sqlfluff-lintable, dbt's philosophy applied to the extract layer. Python orchestrates; SQL declares. |
| **One generic raw table (long format)** | One table per indicator | Adding an indicator = one config line, zero DDL. Pivoting to wide format belongs to dbt staging, not to ingestion. |
| **Dedicated Supabase project** | Shared project with mobility-zgz | Blast radius isolation: a runaway backfill in one project cannot put the other in read-only mode. Credential rotation is independent. Free tier allows 2 active projects. |
| **Pipeline as Supabase keepalive** | Separate ping mechanism | Supabase pauses free projects after 7 days without connections. The daily pipeline generates a connection every run, keeping the project active organically — no additional mechanism needed. Verified empirically on first run attempt. |
| **10-minute raw granularity + hourly aggregation in dbt** | Hourly-only ingestion | ESIOS national generation indicators are natively 10-minute. No hourly aggregate exists at national scope. Raw preserves source fidelity; `date_trunc + sum` in dbt staging produces the hourly grain. Transformation belongs to the transform layer. |
| **geo_id=3 filter in staging, not in extract** | Filter at API request time | The extract layer has no opinion on business logic. Filtering by geography is a transformation decision — it lives in dbt staging where it is documented, tested, and version-controlled alongside the model that uses it. |
| **No cap on manual extraction window** | max_window_days safety cap | 
Single operator (personal portfolio). The operator knows what they're 
doing when they set EXTRACT_START/EXTRACT_END. Enterprise context would 
require chunking and validation; that complexity is not justified here. |

## Setup

1. Request a free ESIOS token: consultasios@ree.es
2. `cp .env.example .env` and fill in credentials (Supabase **session** pooler, port 5432)
3. `pip install -r requirements.txt`
4. `pytest tests/ -q`
5. `python -m extract.main`

## Env vars

| Variable | Purpose |
|---|---|
| `ESIOS_API_TOKEN` | Personal API token issued by REE |
| `DB_HOST` / `DB_PORT` / `DB_NAME` / `DB_USER` / `DB_PASSWORD` | Supabase session-pooler connection |
