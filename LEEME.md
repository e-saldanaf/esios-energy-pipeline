# Pipeline de Datos del Mercado Eléctrico Español (ESIOS)

Proyecto de ingeniería analítica end-to-end sobre el mercado eléctrico español
(API pública de ESIOS/REE). **dbt Core es el protagonista**; todo lo demás existe
para alimentarlo y mostrar su resultado. Coste total de infraestructura: **0 €**.

```
cron-job.org ──▶ workflow_dispatch ──▶ GitHub Actions
                                          │
                    Python extract (ventana de fechas explícita, API ESIOS)
                                          ▼
                          Supabase (Postgres 17, esquema raw)
                                          ▼
                     dbt Core (staging ▸ intermediate ▸ marts)
                          ├── tests + snapshots
                          ├── dbt docs ──▶ GitHub Pages
                          ▼
                     Evidence.dev dashboard estático
```

## Estado del proyecto

| Fase | Estado |
|---|---|
| 1. Capa de extracción (ventana explícita + MERGE + directorio SQL) | ✅ Completada |
| 2. CI/CD (Actions + secrets + keepalive + inputs de backfill manual) | ✅ Completada |
| 3. Capa dbt (modelos, tests, snapshots, docs) | 🔜 Siguiente |
| 4. Dashboard Evidence.dev | 🔜 Pendiente |
| 5. Indicador de demanda + correlación con clima | 🗺️ Roadmap |

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
| 600 | `spot_market_price` | Horaria | 6 países (filtrado a España en staging) |
| 2038 | `generation_wind` | 10 min | Solo España |
| 2040 | `generation_coal` | 10 min | Solo España |
| 2041 | `generation_combined_cycle` | 10 min | Solo España |
| 2042 | `generation_hydro` | 10 min | Solo España |
| 2044 | `generation_solar_pv` | 10 min | Solo España |
| 2051 | `generation_cogen_residues` | 10 min | Solo España |
| 10004 | `generation_total` | 10 min | Solo España |

Todos los IDs verificados contra el catálogo vivo de ESIOS el 22/07/2026.

## Registro de decisiones

Decisiones de arquitectura deliberadas, con el trade-off que acepta cada una.
Esta sección es el verdadero entregable del proyecto de cara a una entrevista.

| Decisión | Alternativa rechazada | Por qué |
|---|---|---|
| **Sin Airflow** | Airflow (lo uso a diario en producción) | Un batch diario sin dependencias entre DAGs no justifica el coste operativo de un orquestador. Elegir NO usar una herramienta que conoces también es una decisión de arquitectura. |
| **cron-job.org → `workflow_dispatch`** | Solo `schedule` de GitHub | Evidencia medida: los crons horarios de `schedule` alcanzaron un ~42% de tasa de éxito en esta cuenta. El dispatch vía API REST arranca en segundos. El cron nativo se mantiene como respaldo. |
| **Ventana de fechas explícita (D-2/D)** | Extracción basada en watermark | El watermark crea estado implícito: el comportamiento del pipeline depende de lo que ya hay en la base de datos. Los parámetros explícitos son más simples, predecibles y fáciles de razonar. La columna `updated_at` responde "¿qué cambió recientemente?" sin ninguna query de watermark. El solape D-2 captura las revisiones de ESIOS de forma gratuita mediante `IS DISTINCT FROM`. |
| **Fecha fin inclusiva para el usuario** | Fin exclusivo (convención de la API) | Los usuarios piensan en fechas de calendario. `EXTRACT_END=2026-01-31` debe cargar el 31 de enero, no detenerse antes. El código suma un día internamente — el límite de la API es un detalle de implementación, no una preocupación del usuario. |
| **Postgres (Supabase) como warehouse** | MotherDuck / DWH columnar | A ~10² filas/día, el almacenamiento columnar no aporta nada. Free tier, el adapter de dbt más maduro, conexión nativa con Evidence. Sé exactamente en qué volumen esta decisión deja de escalar — y migraría a Redshift, que uso en producción. |
| **Session pooler (puerto 5432)** | Conexión directa / transaction pooler | La conexión directa es solo IPv6 → los runners de CI fallan. El transaction pooler destruye las tablas temporales entre sentencias → el patrón MERGE se rompe. El session pooler es la única opción que satisface ambas restricciones simultáneamente. |
| **`MERGE` (SQL:2003)** | `INSERT ... ON CONFLICT` | Estándar ANSI → transferible a Redshift/Snowflake/BigQuery. La rama condicional `WHEN MATCHED AND ... IS DISTINCT FROM` escribe solo los cambios reales. ESIOS revisa los valores publicados — es un caso de negocio real, no código defensivo. Caveat asumido: no es seguro ante escritores concurrentes — aquí solo hay uno. |
| **`IF NOT EXISTS` + `TRUNCATE` en tabla temporal** | `DROP / CREATE` por indicador | DDL dentro de una transacción puede causar commits implícitos. `IF NOT EXISTS` garantiza existencia; `TRUNCATE` garantiza limpieza entre indicadores en la misma conexión. Descubierto y corregido en la primera ejecución en producción. |
| **SQL en ficheros `.sql`** | SQL como strings en Python | Diffs revisables, lintable con sqlfluff, resaltado de sintaxis en el IDE. Python orquesta; SQL declara. La filosofía de dbt aplicada a la capa de extracción. |
| **Una única tabla raw en formato largo** | Una tabla por indicador | Añadir un indicador = una línea de config, cero DDL. El pivotado a formato ancho pertenece al staging de dbt, no a la ingesta. |
| **Granularidad raw de 10 minutos, horaria en staging** | Ingesta solo horaria | Los indicadores nacionales de generación de ESIOS son nativamente diezminutales. No existe un agregado horario nacional. Raw preserva la fidelidad de la fuente; `date_trunc + sum` en dbt staging produce el grano horario. La transformación pertenece a la capa de transformación. |
| **Filtro `geo_id=3` en staging, no en el extract** | Filtrar en la llamada a la API | La capa de extracción no tiene opinión sobre lógica de negocio. Filtrar por geografía es una decisión de transformación — documentada, testeada y versionada junto al modelo que la usa. |
| **Proyecto Supabase dedicado** | Proyecto compartido con mobility-zgz | Aislamiento del blast radius: un backfill descontrolado en un proyecto no puede poner al otro en modo solo-lectura. La rotación de credenciales es independiente. El free tier permite 2 proyectos activos. |
| **El pipeline como keepalive de Supabase** | Mecanismo de ping separado | Supabase pausa los proyectos gratuitos tras 7 días sin conexiones. El pipeline diario genera una conexión en cada ejecución, manteniendo el proyecto activo de forma orgánica. Verificado empíricamente en el primer intento de ejecución. |
| **Sin límite en la ventana de extracción manual** | Cap de `max_window_days` | Operador único (portfolio personal). El operador sabe lo que hace al configurar `EXTRACT_START`/`EXTRACT_END`. Un contexto enterprise requeriría chunking y validación; esa complejidad no está justificada aquí. |
| **Formateador de logs dual (text/json)** | Solo JSON | Los logs JSON son para máquinas. `LOG_FORMAT=text` (por defecto en local) produce salida legible con colores en el terminal de VS Code. `LOG_FORMAT=json` (configurado a nivel de job en CI) produce logs estructurados para GitHub Actions. Se usa `os.getenv` directamente — importar `settings` aquí crearía una dependencia circular en tiempo de carga del módulo. |
| **Feature flag `DBT_ENABLED`** | Desplegar los steps de dbt inmediatamente | El proyecto dbt aún no existe. El flag permite que el pipeline corra en verde en CI hoy y activa el flujo completo cuando dbt aterrice — sin reescribir el YAML, sin runs en rojo entre medias. Entrega progresiva aplicada a un pipeline de datos. |

## Configuración

### Requisitos previos

- Python 3.12+
- Entorno conda con `pip install -r requirements.txt`
- Token gratuito de ESIOS: email a `consultasios@ree.es`
- Proyecto Supabase (free tier, Postgres 17)

### Configuración local

```bash
cp .env.example .env
# Rellena ESIOS_API_TOKEN y credenciales del session pooler de Supabase (puerto 5432)

pip install -r requirements.txt
pytest tests/ -q                    # 5 tests, deben estar en verde
python -m scripts.check_connection  # valida la BD + provisiona el esquema raw
python -m extract.main              # modo automático: carga D-2 hasta hoy
```

### Configuraciones de VS Code (`.vscode/launch.json`)

Tres configuraciones disponibles en Run & Debug (`Ctrl+Shift+D`):

| Configuración | Modo | Variables de entorno |
|---|---|---|
| Extract: automático | D-2 hasta hoy | ninguna |
| Extract: backfill manual | Rango de fechas personalizado | `EXTRACT_START`, `EXTRACT_END` |
| Check connection | Smoke test | ninguna |

### Configuración de GitHub Actions

Ver `docs/SETUP_CICD.md` para el checklist completo de configuración única:
secrets, PAT fine-grained, job de cron-job.org y configuración de GitHub Pages.

## Variables de entorno

| Variable | Obligatoria | Propósito |
|---|---|---|
| `ESIOS_API_TOKEN` | ✅ | Token personal emitido por REE |
| `DB_HOST` | ✅ | Host del session pooler de Supabase |
| `DB_PORT` | por defecto 5432 | Puerto Postgres — debe ser 5432 (modo session) |
| `DB_NAME` | por defecto postgres | Nombre de la base de datos |
| `DB_USER` | ✅ | `postgres.<project-ref>` |
| `DB_PASSWORD` | ✅ | Contraseña de la base de datos de Supabase |
| `EXTRACT_START` | opcional | Inicio de backfill manual (`yyyy-mm-dd`, inclusivo) |
| `EXTRACT_END` | opcional | Fin de backfill manual (`yyyy-mm-dd`, inclusivo) |
| `LOG_FORMAT` | por defecto text | `text` (local) o `json` (CI) |

## Estructura del repositorio

```
esios-energy-pipeline/
├── .github/workflows/daily_pipeline.yml   # CI/CD: extract + dbt (gated) + keepalive
├── docs/SETUP_CICD.md                     # Checklist de configuración única de CI/CD
├── extract/
│   ├── config.py                          # pydantic-settings + registro de indicadores
│   ├── esios_client.py                    # Cliente API con retry + timeout
│   ├── loader.py                          # Patrón stage-then-MERGE
│   ├── logging_setup.py                   # Formateador dual (text/json)
│   ├── main.py                            # Entrypoint del pipeline
│   ├── sql_loader.py                      # Carga ficheros .sql con lru_cache
│   ├── watermark.py                       # Lógica de ventana de fechas explícita
│   └── sql/
│       ├── ddl/create_raw_schema.sql      # Esquema raw idempotente + tabla
│       ├── ddl/create_temp_staging.sql    # Patrón IF NOT EXISTS + TRUNCATE
│       └── merge/merge_indicator_values.sql  # MERGE ANSI con IS DISTINCT FROM
├── dbt/                                   # 🔜 Fase 3
├── evidence/                              # 🔜 Fase 4
├── scripts/
│   ├── check_connection.py                # Smoke test de conectividad
│   └── discover_indicators.py             # Explorador del catálogo ESIOS
├── tests/
│   └── test_loader.py                     # Tests unitarios de normalise_values
├── .env.example
├── README.md                              # English version
├── LEEME.md                               # Versión en castellano
└── requirements.txt
```