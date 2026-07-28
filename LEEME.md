# Pipeline de Datos del Mercado Eléctrico Español (ESIOS)

![Python](https://img.shields.io/badge/Python-3.12-306998?logo=python&logoColor=white)
![dbt](https://img.shields.io/badge/dbt-1.9.2-FF694B?logo=dbt&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-336791?logo=postgresql&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-CI%2FCD-2088FF?logo=githubactions&logoColor=white)
![Netlify](https://img.shields.io/badge/Netlify-Dashboard-00C7B7?logo=netlify&logoColor=white)
![Supabase](https://img.shields.io/badge/Supabase-Free_Tier-3ECF8E?logo=supabase&logoColor=white)

Proyecto de ingeniería analítica end-to-end sobre el mercado eléctrico español
(API pública de ESIOS/REE). **dbt Core es el protagonista**; todo lo demás existe
para alimentarlo y mostrar su resultado. Coste total de infraestructura: **0 €**.

🔗 **[Dashboard en vivo](https://tranquil-stroopwafel-f7f9d0.netlify.app)** · **[dbt Docs y Lineage](https://e-saldanaf.github.io/esios-energy-pipeline/)**

```
cron-job.org ──▶ workflow_dispatch ──▶ GitHub Actions
                                          │
                    Python extract (ventana de fechas explícita, API ESIOS)
                                          ▼
                          Supabase (Postgres 17, esquema raw)
                                          ▼
                     dbt Core (staging ▸ intermediate ▸ marts)
                          ├── 17 tests (fuente + modelos)
                          ├── dbt docs ──▶ GitHub Pages
                          ▼
                     Evidence.dev dashboard estático ──▶ Netlify
```

## Estado del proyecto

| Fase | Estado |
|---|---|
| 1. Capa de extracción (ventana explícita + MERGE + directorio SQL) | ✅ Completada |
| 2. CI/CD (Actions + secrets + keepalive + inputs de backfill manual) | ✅ Completada |
| 3. Capa dbt (staging, intermediate, marts, tests, docs) | ✅ Completada |
| 4. Dashboard Evidence.dev → Netlify | ✅ Completada |
| 5. cron-job.org (scheduling preciso) | 🔜 Pendiente |
| 6. Indicador de demanda + correlación con clima | 🗺️ Roadmap |

## Arquitectura

### Capa de extracción

El pipeline se ejecuta diariamente mediante GitHub Actions, disparado por
cron-job.org a través de `workflow_dispatch` (trigger principal) con un
`schedule` nativo como respaldo de último recurso.

Dos modos de extracción:

**Automático (cron diario):** carga desde D-2 hasta hoy. El solape de D-2
captura las revisiones de valores que ESIOS publica días después de la
publicación inicial. La rama `IS DISTINCT FROM` del MERGE recoge esas
correcciones de forma gratuita.

**Manual (backfill):** controlado por las variables de entorno `EXTRACT_START`
y `EXTRACT_END` (formato `yyyy-mm-dd`, fin inclusivo). Se configuran en el
formulario de `workflow_dispatch` de GitHub Actions o localmente mediante
`launch.json`. Sin límite de ventana — proyecto de operador único.

```bash
# Backfill manual en local
EXTRACT_START=2025-01-01 EXTRACT_END=2025-12-31 python -m extract.main
```

### Esquema raw

Una única tabla genérica en formato largo (`raw.esios_indicator_values`) para
todos los indicadores. Añadir un indicador nuevo requiere cero DDL — solo una
línea en `extract/config.py`. El esquema se autoprovisiona en la primera
ejecución (DDL idempotente).

| Columna | Tipo | Descripción |
|---|---|---|
| `indicator_id` | integer | ID del indicador ESIOS |
| `datetime_utc` | timestamptz | Siempre almacenado en UTC |
| `geo_id` | integer | Geografía (3 = España peninsular) |
| `value` | numeric | Nullable — ESIOS puede publicar nulos |
| `extracted_at` | timestamptz | Timestamp de primera carga |
| `updated_at` | timestamptz | Última actualización por MERGE |

Clave primaria: `(indicator_id, datetime_utc, geo_id)` — garantiza idempotencia.

### Indicadores

| ID | Slug | Granularidad | Ámbito geográfico |
|---|---|---|---|
| 600 | `spot_market_price` | 10 min | 6 países (filtrado a España en staging) |
| 2038 | `generation_wind` | 10 min | Solo España |
| 2040 | `generation_coal` | 10 min | Solo España |
| 2041 | `generation_combined_cycle` | 10 min | Solo España |
| 2042 | `generation_hydro` | 10 min | Solo España |
| 2044 | `generation_solar_pv` | 10 min | Solo España |
| 2051 | `generation_cogen_residues` | 10 min | Solo España |
| 10004 | `generation_total` | 10 min | Solo España |

Todos los IDs verificados contra el catálogo vivo de ESIOS el 22/07/2026.
Todos los indicadores son nativamente diezminutales. El precio se agrega a
horario mediante `avg` en staging; la generación mediante `sum`. Ambos se
unen al grano horario en intermediate.

### Capa dbt

```
fuentes (_sources.yml)
    raw.esios_indicator_values  ← freshness: warn 36h, error 72h
            │
    ┌───────┴────────┐
    ▼                ▼
stg_esios__      stg_esios__       stg_esios__
hourly_prices    generation        technologies
(vista)          (vista)           (vista, seed)
    │                │
    └───────┬────────┘
            ▼
    int_hourly_market
    (vista — join precio × generación)
            │
            ▼
    fct_hourly_market          ← 13.635 filas, tabla
            │
    ┌───────┴──────────────────┐
    ▼                          ▼
mart_daily_summary      mart_renewables_price_impact
(tabla)                 (tabla — merit order effect)
    │
    ▼
mart_technology_mix
(tabla — mix mensual de generación)
```

**17 tests de datos:** 4 `not_null` sobre la fuente + 13 `unique`/`not_null` sobre los marts.

**dbt docs:** publicados en GitHub Pages en cada ejecución de CI.

### Dashboard Evidence.dev

4 páginas desplegadas en Netlify, reconstruidas en cada ejecución de CI:

| Página | Contenido |
|---|---|
| **Home** | KPIs (30d) + precio diario + mix del último mes |
| **Precio Spot** | Histórico completo de precio + tendencia mensual vs renovables + horas de precio negativo |
| **Impacto Renovable** | Scatter del merit order effect + precio por bucket de renovable |
| **Mix Tecnológico** | Evolución mensual renovable/fósil + área apilada MWh + días con precio negativo |

## Registro de decisiones

| Decisión | Alternativa rechazada | Por qué |
|---|---|---|
| **Sin Airflow** | Airflow (lo uso a diario en producción) | Un batch diario sin dependencias entre DAGs no justifica el coste operativo de un orquestador. Elegir NO usar una herramienta que conoces también es una decisión de arquitectura. |
| **cron-job.org → `workflow_dispatch`** | Solo `schedule` de GitHub | Evidencia medida: ~42% de tasa de éxito en crons horarios. El dispatch vía API REST arranca en segundos. El cron nativo se mantiene como respaldo. |
| **Ventana de fechas explícita (D-2/D)** | Extracción basada en watermark | El watermark crea estado implícito. Los parámetros explícitos son más simples y predecibles. `updated_at` responde "¿qué cambió?" sin query de watermark. El solape D-2 captura revisiones de ESIOS via `IS DISTINCT FROM`. |
| **Fecha fin inclusiva para el usuario** | Fin exclusivo (convención de la API) | Los usuarios piensan en fechas de calendario. El código suma un día internamente. |
| **Postgres (Supabase) como warehouse** | MotherDuck / DWH columnar | A ~10² filas/día el columnar no aporta nada. Free tier, adapter de dbt más maduro. Sé exactamente cuándo esta decisión deja de escalar — y migraría a Redshift, que uso en producción. |
| **Session pooler (puerto 5432)** | Conexión directa / transaction pooler | La conexión directa es solo IPv6 → los runners de CI fallan. El transaction pooler destruye tablas temporales → el patrón MERGE se rompe. El session pooler satisface ambas restricciones simultáneamente. |
| **`MERGE` (SQL:2003)** | `INSERT ... ON CONFLICT` | Estándar ANSI → transferible a Redshift/Snowflake/BigQuery. `IS DISTINCT FROM` escribe solo los cambios reales. ESIOS revisa valores publicados — caso de negocio real. |
| **`IF NOT EXISTS` + `TRUNCATE` en tabla temporal** | `DROP / CREATE` por indicador | Descubierto en la primera ejecución en producción. El rollback de un savepoint no destruye tablas temporales — `IF NOT EXISTS` + `TRUNCATE` hace el loader idempotente entre indicadores. |
| **SQL en ficheros `.sql`** | SQL como strings en Python | Diffs revisables, lintable con sqlfluff. Python orquesta; SQL declara. La filosofía de dbt aplicada a la capa de extracción. |
| **Una única tabla raw en formato largo** | Una tabla por indicador | Añadir un indicador = una línea de config, cero DDL. El pivotado pertenece al staging de dbt. |
| **Granularidad raw de 10 minutos, horaria en staging** | Ingesta solo horaria | Los indicadores nacionales de ESIOS son nativamente diezminutales. Raw preserva la fidelidad de la fuente; `date_trunc + sum/avg` produce el grano horario. |
| **`avg` para precio, `sum` para generación** | Ambos `sum` o ambos `avg` | El precio es una tasa (€/MWh) — la media es semánticamente correcta. La generación es energía (MWh) — aditiva, por tanto la suma es correcta. La semántica del dominio determina la función de agregación. |
| **Filtro `geo_id=3` en staging, no en el extract** | Filtrar en la llamada a la API | El extract no tiene opinión sobre lógica de negocio. Filtrar por geografía es una decisión de transformación — documentada y testeada junto al modelo que la usa. |
| **Proyecto Supabase dedicado** | Proyecto compartido con mobility-zgz | Aislamiento del blast radius. Rotación de credenciales independiente. El free tier permite 2 proyectos activos. |
| **El pipeline como keepalive de Supabase** | Mecanismo de ping separado | Supabase pausa proyectos tras 7 días sin conexiones. El pipeline diario lo mantiene activo de forma orgánica. Verificado empíricamente. |
| **Sin límite en la ventana de extracción manual** | Cap de `max_window_days` | Operador único. Un contexto enterprise requeriría chunking; esa complejidad no está justificada aquí. |
| **Formateador de logs dual (text/json)** | Solo JSON | `LOG_FORMAT=text` en local (con colores); `LOG_FORMAT=json` en CI (estructurado). `os.getenv` directo — importar `settings` crearía dependencia circular. |
| **Feature flag `DBT_ENABLED`** | Desplegar steps de dbt inmediatamente | Permite que el pipeline corra en verde en CI antes de que dbt esté listo. Sin reescribir el YAML al activarlo. |
| **`profiles.yml` en el repo (sin credenciales)** | Solo `~/.dbt/profiles.yml` | Los runners de CI no tienen directorio home. `env_var()` lee los secrets inyectados por GitHub Actions — seguro para commitear. |
| **Evidence.dev en Netlify, dbt docs en GitHub Pages** | Ambos en GitHub Pages | GitHub Pages ya ocupado por dbt docs. Dos URLs separadas mantiene cada herramienta en su sitio — narrativa más limpia y cero conflicto. |
| **`npm run sources && npm run build` como build command de Netlify** | Solo `npm run build` | Evidence necesita descargar los datos de Supabase antes de construir. Las fuentes deben ejecutarse primero — descubierto en el primer deploy de Netlify. |

## Configuración

### Requisitos previos

- Python 3.12+ (entorno conda `dbt-course` recomendado)
- dbt Core 1.9.2 + dbt-postgres 1.9.0
- Node.js 20+ (para Evidence)
- Token gratuito de ESIOS: email a `consultasios@ree.es`
- Proyecto Supabase dedicado (free tier, Postgres 17)

### Configuración local

```bash
cp .env.example .env
# Rellena ESIOS_API_TOKEN y credenciales del session pooler de Supabase (puerto 5432)

pip install -r requirements.txt
pytest tests/ -q                    # 5 tests en verde
python -m scripts.check_connection  # valida BD + provisiona esquema raw
python -m extract.main              # modo automático: carga D-2 hasta hoy

cd dbt/esios_energy
dbt build                           # seed + run + test (26 en verde)
dbt docs generate --static          # genera docs/index.html
dbt docs serve                      # preview en localhost:8080

cd ../../evidence
npm install
NODE_TLS_REJECT_UNAUTHORIZED=0 npm run sources   # descarga datos de Supabase
npm run dev                          # preview en localhost:3000
```

### Configuraciones de VS Code (`.vscode/launch.json`)

| Configuración | Modo |
|---|---|
| Extract: automático | D-2 hasta hoy |
| Extract: backfill manual | Rango personalizado via `EXTRACT_START` / `EXTRACT_END` |
| Check connection | Smoke test |

### Configuración de GitHub Actions

Ver `docs/SETUP_CICD.md` para el checklist completo.

Activar dbt en CI: **Settings → Secrets and variables → Actions → Variables → `DBT_ENABLED=true`**

## Enlaces

| Recurso | URL |
|---|---|
| Dashboard en vivo | https://tranquil-stroopwafel-f7f9d0.netlify.app |
| dbt docs y lineage | https://e-saldanaf.github.io/esios-energy-pipeline/ |

## Variables de entorno

| Variable | Obligatoria | Propósito |
|---|---|---|
| `ESIOS_API_TOKEN` | ✅ | Token personal emitido por REE |
| `DB_HOST` | ✅ | Host del session pooler de Supabase |
| `DB_PORT` | por defecto 5432 | Debe ser 5432 (modo session) |
| `DB_NAME` | por defecto postgres | Nombre de la base de datos |
| `DB_USER` | ✅ | `postgres.<project-ref>` |
| `DB_PASSWORD` | ✅ | Contraseña de Supabase |
| `EXTRACT_START` | opcional | Inicio de backfill manual (`yyyy-mm-dd`, inclusivo) |
| `EXTRACT_END` | opcional | Fin de backfill manual (`yyyy-mm-dd`, inclusivo) |
| `LOG_FORMAT` | por defecto text | `text` (local) o `json` (CI) |

## Estructura del repositorio

```
esios-energy-pipeline/
├── .github/workflows/daily_pipeline.yml
├── docs/SETUP_CICD.md
├── dbt/esios_energy/
│   ├── dbt_project.yml
│   ├── profiles.yml                       # solo env_var(), seguro para commitear
│   ├── seeds/technologies.csv             # catálogo de 6 tecnologías
│   └── models/
│       ├── staging/
│       │   ├── _sources.yml               # fuente + freshness + 4 tests
│       │   ├── stg_esios__hourly_prices.sql
│       │   ├── stg_esios__generation.sql
│       │   └── stg_esios__technologies.sql
│       ├── intermediate/
│       │   └── int_hourly_market.sql
│       └── marts/
│           ├── _marts.yml                 # 13 tests
│           ├── fct_hourly_market.sql
│           ├── mart_daily_summary.sql
│           ├── mart_renewables_price_impact.sql
│           └── mart_technology_mix.sql
├── evidence/
│   ├── sources/supabase/                  # queries SQL + config de conexión
│   └── pages/
│       ├── index.md                       # Home — KPIs + precio 30d
│       ├── precio.md                      # Histórico de precio
│       ├── renovables.md                  # Merit order effect
│       └── tecnologias.md                # Mix tecnológico
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
├── README.md                              # Versión en inglés
├── LEEME.md                               # Este fichero
└── requirements.txt
```