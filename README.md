# ESIOS Energy Pipeline

![Python](https://img.shields.io/badge/Python-3.12-306998?logo=python&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.9.2-FF694B?logo=dbt&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?logo=githubactions&logoColor=white)
![Netlify](https://img.shields.io/badge/Netlify-Dashboard-00C7B7?logo=netlify&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Free_Tier-3ECF8E?logo=supabase&logoColor=white)

End-to-end analytics engineering project on the Spanish electricity market
(ESIOS/REE public API). **dbt Core is the star**; everything else exists to
feed it and show its output. Total infrastructure cost: **0 €**.

🔗 **[Live Dashboard](https://esios-energy-es.netlify.app/)** · **[dbt Docs & Lineage](https://e-saldanaf.github.io/esios-energy-pipeline/)**

```
cron-job.org ──▶ workflow_dispatch ──▶ GitHub Actions
                                          │
                    Python extract (explicit date window, ESIOS API)
                                          ▼
                          Supabase (Postgres 17, schema raw)
                                          ▼
                     dbt Core (staging ▸ intermediate ▸ marts)
                          ├── 17 tests (source + models)
                          ├── dbt docs ──▶ GitHub Pages
                          ▼
                     Evidence.dev static dashboard ──▶ Netlify
```

## Project status

| Phase | Status |
|---|---|
| 1. Extract layer (explicit window + MERGE + SQL directory) | ✅ Complete |
| 2. CI/CD (Actions + secrets + keepalive + manual backfill inputs) | ✅ Complete |
| 3. dbt layer (staging, intermediate, marts, tests, docs) | ✅ Complete |
| 4. Evidence.dev dashboard → Netlify | ✅ Complete |
| 5. cron-job.org (precise scheduling) | 🔜 Pending |
| 6. Demand indicator + weather correlation | 🗺️ Roadmap |

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
| 600 | `spot_market_price` | 10-min | 6 countries (filtered to Spain in staging) |
| 2038 | `generation_wind` | 10-min | Spain only |
| 2040 | `generation_coal` | 10-min | Spain only |
| 2041 | `generation_combined_cycle` | 10-min | Spain only |
| 2042 | `generation_hydro` | 10-min | Spain only |
| 2044 | `generation_solar_pv` | 10-min | Spain only |
| 2051 | `generation_cogen_residues` | 10-min | Spain only |
| 10004 | `generation_total` | 10-min | Spain only |

All IDs verified against the live ESIOS catalogue on 2026-07-22.
All indicators are natively 10-minute. Price is aggregated to hourly via `avg`
in staging; generation via `sum`. Both are joined at hourly grain in intermediate.

### dbt layer

```
sources (_sources.yml)
    raw.esios_indicator_values  ← freshness: warn 36h, error 72h
            │
    ┌───────┴────────┐
    ▼                ▼
stg_esios__      stg_esios__       stg_esios__
hourly_prices    generation        technologies
(view)           (view)            (view, seed)
    │                │
    └───────┬────────┘
            ▼
    int_hourly_market
    (view — price × generation join)
            │
            ▼
    fct_hourly_market          ← 13,635 rows, table
            │
    ┌───────┴──────────────────┐
    ▼                          ▼
mart_daily_summary      mart_renewables_price_impact
(table)                 (table — merit order effect)
    │
    ▼
mart_technology_mix
(table — monthly generation mix)
```

**17 data tests:** 4 source `not_null` + 13 model `unique`/`not_null` on marts.

**dbt docs:** published to GitHub Pages on every CI run.

### Evidence.dev dashboard

4 pages deployed on Netlify, rebuilt on every CI run:

| Page | Content |
|---|---|
| **Home** | KPIs (30d) + daily price chart + last month mix |
| **Precio Spot** | Full price history + monthly trend vs renewables + negative price hours |
| **Impacto Renovable** | Merit order effect scatter + price by renewable bucket |
| **Mix Tecnológico** | Monthly renewable/fossil evolution + stacked MWh area + negative price days |

## Decisions log

| Decision | Alternative rejected | Why |
|---|---|---|
| **No Airflow** | Airflow (daily driver at work) | A single daily batch with no cross-DAG dependencies doesn't justify an orchestrator's operational cost. Choosing NOT to use a tool you know is an architecture decision too. |
| **cron-job.org → `workflow_dispatch`** | GitHub `schedule` alone | Measured evidence: hourly `schedule` crons achieved ~42% hit rate on this account. Dispatch via REST API starts in seconds. Native cron kept as fallback. |
| **Explicit date window (D-2/D)** | Watermark-based extraction | Watermark creates implicit state. Explicit parameters are simpler, more predictable, and easier to reason about. `updated_at` answers "what changed recently?" without any watermark query. D-2 overlap captures ESIOS revisions via `IS DISTINCT FROM`. |
| **Inclusive end date UX** | Exclusive end (API convention) | Users think in calendar dates. The code adds one day internally — API boundary is an implementation detail. |
| **Postgres (Supabase) as warehouse** | MotherDuck / columnar DWH | At ~10² rows/day, columnar storage buys nothing. Free tier, most mature dbt adapter. I know exactly at which volume this stops scaling — and I'd move to Redshift, which I run in production. |
| **Session pooler (port 5432)** | Direct connection / transaction pooler | Direct connection is IPv6-only → CI runners fail. Transaction pooler destroys temp tables → MERGE pattern breaks. Session pooler satisfies both constraints simultaneously. |
| **`MERGE` (SQL:2003)** | `INSERT ... ON CONFLICT` | ANSI standard → transferable to Redshift/Snowflake/BigQuery. `IS DISTINCT FROM` writes only real changes. ESIOS revises published values — real business case, not boilerplate. |
| **`IF NOT EXISTS` + `TRUNCATE` on temp table** | `DROP / CREATE` per indicator | Discovered on first production run. Savepoint rollback doesn't destroy temp tables — `IF NOT EXISTS` + `TRUNCATE` makes the loader idempotent across indicators. |
| **SQL in `.sql` files** | SQL strings inside Python | Reviewable diffs, sqlfluff-lintable. Python orchestrates; SQL declares. dbt's philosophy applied to the extract layer. |
| **One generic raw table (long format)** | One table per indicator | Adding an indicator = one config line, zero DDL. Pivoting belongs to dbt staging. |
| **10-minute raw, hourly in staging** | Hourly-only ingestion | ESIOS national indicators are natively 10-minute. Raw preserves source fidelity; `date_trunc + sum/avg` in staging produces hourly grain. Transformation belongs to the transform layer. |
| **`avg` for price, `sum` for generation** | Both `sum` or both `avg` | Price is a rate (€/MWh) — average is semantically correct. Generation is energy (MWh) — additive, so sum is correct. Domain semantics drive the aggregation function. |
| **`geo_id=3` filter in staging, not in extract** | Filter at API request time | Extract has no opinion on business logic. Geography filtering is a transformation decision — documented and tested alongside the model that uses it. |
| **Dedicated Supabase project** | Shared project with mobility-zgz | Blast radius isolation. Credential rotation is independent. Free tier allows 2 active projects. |
| **Pipeline as Supabase keepalive** | Separate ping mechanism | Supabase pauses free projects after 7 days. Daily pipeline keeps it active organically. Verified empirically on first run. |
| **No cap on manual extraction window** | `max_window_days` safety cap | Single operator. Enterprise context would require chunking; that complexity is not justified here. |
| **Dual log formatter (text/json)** | JSON-only | `LOG_FORMAT=text` locally (coloured); `LOG_FORMAT=json` in CI (structured). `os.getenv` used directly — importing `settings` here would create a circular dependency. |
| **`DBT_ENABLED` feature flag** | Deploy dbt steps immediately | Lets the pipeline run green in CI before dbt is ready. No YAML rewrite when activating. Progressive delivery applied to a data pipeline. |
| **`profiles.yml` in repo (no credentials)** | `~/.dbt/profiles.yml` only | CI runners have no home directory. `env_var()` in profiles.yml reads secrets injected by GitHub Actions — safe to commit, zero credentials hardcoded. |
| **Evidence.dev on Netlify, dbt docs on GitHub Pages** | Both on GitHub Pages | GitHub Pages already occupied by dbt docs. Two separate URLs keeps each tool in its own space — cleaner narrative and zero conflict. |
| **`npm run sources && npm run build` as Netlify build command** | `npm run build` alone | Evidence needs to download data from Supabase before building. Sources must run first — discovered on first Netlify deploy. |

## Setup

### Prerequisites

- Python 3.12+ (conda env `dbt-course` recommended)
- dbt Core 1.9.2 + dbt-postgres 1.9.0
- Node.js 20+ (for Evidence)
- Free ESIOS token: email `consultasios@ree.es`
- Supabase project (free tier, Postgres 17, dedicated project)

### Local setup

```bash
cp .env.example .env
# Fill in ESIOS_API_TOKEN and Supabase session-pooler credentials (port 5432)

pip install -r requirements.txt
pytest tests/ -q                    # 5 tests, should be green
python -m scripts.check_connection  # validates DB + provisions raw schema
python -m extract.main              # automatic mode: loads D-2 to today

cd dbt/esios_energy
dbt build                           # seed + run + test (26 passing)
dbt docs generate --static          # generates docs/index.html
dbt docs serve                      # preview at localhost:8080

cd ../../evidence
npm install
NODE_TLS_REJECT_UNAUTHORIZED=0 npm run sources   # download data from Supabase
npm run dev                         # preview at localhost:3000
```

### VS Code launch configurations (`.vscode/launch.json`)

| Configuration | Mode |
|---|---|
| Extract: automatic | D-2 to today |
| Extract: manual backfill | Custom date range via `EXTRACT_START` / `EXTRACT_END` |
| Check connection | Smoke test |

### GitHub Actions setup

See `docs/SETUP_CICD.md` for the complete one-time checklist.

Activate dbt in CI: **Settings → Secrets and variables → Actions → Variables → `DBT_ENABLED=true`**

## Links

| Resource | URL |
|---|---|
| Live dashboard | https://esios-energy-es.netlify.app/ |
| dbt docs + lineage | https://e-saldanaf.github.io/esios-energy-pipeline/ |

## Env vars

| Variable | Required | Purpose |
|---|---|---|
| `ESIOS_API_TOKEN` | ✅ | Personal API token issued by REE |
| `DB_HOST` | ✅ | Supabase session-pooler host |
| `DB_PORT` | default 5432 | Must be 5432 (session mode) |
| `DB_NAME` | default postgres | Database name |
| `DB_USER` | ✅ | `postgres.<project-ref>` |
| `DB_PASSWORD` | ✅ | Supabase database password |
| `EXTRACT_START` | optional | Manual backfill start (`yyyy-mm-dd`, inclusive) |
| `EXTRACT_END` | optional | Manual backfill end (`yyyy-mm-dd`, inclusive) |
| `LOG_FORMAT` | default text | `text` (local) or `json` (CI) |

## Repository structure

```
esios-energy-pipeline/
├── .github/workflows/daily_pipeline.yml
├── docs/SETUP_CICD.md
├── dbt/esios_energy/
│   ├── dbt_project.yml
│   ├── profiles.yml                      # env_var() only, safe to commit
│   ├── seeds/technologies.csv            # 6 technologies catalogue
│   └── models/
│       ├── staging/
│       │   ├── _sources.yml              # source + freshness + 4 tests
│       │   ├── stg_esios__hourly_prices.sql
│       │   ├── stg_esios__generation.sql
│       │   └── stg_esios__technologies.sql
│       ├── intermediate/
│       │   └── int_hourly_market.sql
│       └── marts/
│           ├── _marts.yml                # 13 tests
│           ├── fct_hourly_market.sql
│           ├── mart_daily_summary.sql
│           ├── mart_renewables_price_impact.sql
│           └── mart_technology_mix.sql
├── evidence/
│   ├── sources/supabase/                 # SQL queries + connection config
│   └── pages/
│       ├── index.md                      # Home — KPIs + 30d price
│       ├── precio.md                     # Price history
│       ├── renovables.md                 # Merit order effect
│       └── tecnologias.md               # Technology mix
├── extract/
│   ├── config.py
│   ├── esios_client.py
│   ├── loader.py
│   ├── logging_setup.py
│   ├── main.py
│   ├── sql_loader.py
│   ├── watermark.py
│   └── sql/
│       ├── ddl/create_raw_schema.sql
│       ├── ddl/create_temp_staging.sql
│       └── merge/merge_indicator_values.sql
├── scripts/
│   ├── check_connection.py
│   └── discover_indicators.py
├── tests/test_loader.py
├── .env.example
├── README.md
├── LEEME.md
└── requirements.txt
```