-- Per-run temporary staging table (MERGE source).
--
-- DIDACTIC NOTE — Why IF NOT EXISTS + TRUNCATE instead of DROP/CREATE:
--   The first indicator creates the table. Subsequent indicators in the
--   same connection reuse it (IF NOT EXISTS = no error) and TRUNCATE
--   empties it before loading new rows. This is safer than DROP/CREATE
--   per indicator because:
--   1. DDL inside a transaction can cause implicit commits on some drivers.
--   2. TRUNCATE is faster than DROP+CREATE for small tables.
--   3. ON COMMIT DROP still fires at connection close, so cleanup is free.
--
-- Root cause of the DuplicateTable bug: conn.transaction() opens a nested
-- savepoint, not a real transaction. Rolling back a savepoint does NOT
-- destroy temp tables created at connection scope. IF NOT EXISTS + TRUNCATE
-- makes the loader idempotent across indicators in the same connection.

CREATE TEMPORARY TABLE IF NOT EXISTS tmp_indicator_values (
    indicator_id   integer      NOT NULL,
    datetime_utc   timestamptz  NOT NULL,
    geo_id         integer      NOT NULL DEFAULT 0,
    value          numeric      NULL
) ON COMMIT DROP;

TRUNCATE tmp_indicator_values;
