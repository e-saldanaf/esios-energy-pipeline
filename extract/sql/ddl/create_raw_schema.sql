-- DDL: raw landing zone.
--
-- DIDACTIC NOTE — One generic long-format table instead of one table per
-- indicator. Adding a new ESIOS indicator requires zero DDL changes.
-- Pivoting to wide format is deliberately NOT done here: reshaping is a
-- transformation concern and belongs to dbt's staging layer.
--
-- The composite PK is what makes MERGE (and idempotency) possible:
-- re-running the pipeline over the same window can never duplicate rows.

CREATE SCHEMA IF NOT EXISTS raw;

CREATE TABLE IF NOT EXISTS raw.esios_indicator_values (
    indicator_id   integer      NOT NULL,
    datetime_utc   timestamptz  NOT NULL,
    geo_id         integer      NOT NULL DEFAULT 0,  -- ESIOS splits some indicators by geography
    value          numeric      NULL,                -- API can publish nulls; staging decides policy
    extracted_at   timestamptz  NOT NULL DEFAULT now(),
    updated_at     timestamptz  NOT NULL DEFAULT now(),
    CONSTRAINT pk_esios_indicator_values
        PRIMARY KEY (indicator_id, datetime_utc, geo_id)
);

COMMENT ON TABLE raw.esios_indicator_values IS
    'Landing zone for ESIOS API indicator values. Long format, append/merge only. Never consumed directly by BI: dbt staging is the contract.';
