-- Per-run temporary staging table (MERGE source).
--
-- DIDACTIC NOTE — Why stage-then-merge instead of merging row by row:
-- this is the canonical warehouse loading pattern. On Redshift you'd COPY
-- from S3 into a staging table and MERGE from there; here the temp table
-- plays the role of that staging zone. Same architecture, smaller scale.
--
-- ON COMMIT DROP: the table disappears when the transaction ends — no
-- cleanup code, no leftovers if the run crashes mid-way. This is also why
-- we need Supabase's SESSION pooler: transaction-mode pooling can hand
-- each statement a different backend, losing the temp table.

CREATE TEMPORARY TABLE tmp_indicator_values (
    indicator_id   integer      NOT NULL,
    datetime_utc   timestamptz  NOT NULL,
    geo_id         integer      NOT NULL DEFAULT 0,
    value          numeric      NULL
) ON COMMIT DROP;
