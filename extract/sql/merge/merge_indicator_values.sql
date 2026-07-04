-- MERGE from the per-run temp staging table into the raw landing table.
--
-- DIDACTIC NOTES:
--
-- 1. MERGE (SQL:2003) vs INSERT..ON CONFLICT:
--    MERGE is ANSI standard — the same statement works on Redshift,
--    Snowflake and BigQuery, so this pattern is transferable knowledge.
--    Requires Postgres 15+ (Supabase: OK).
--
-- 2. Conditional UPDATE branch:
--    `AND target.value IS DISTINCT FROM source.value` means we only write
--    when the value actually changed. ESIOS revises published values
--    (measured generation gets corrected days later), so updates are a
--    real business case here — not defensive boilerplate. IS DISTINCT FROM
--    (instead of <>) handles NULLs correctly: NULL <> 5 is NULL (falsy),
--    NULL IS DISTINCT FROM 5 is TRUE.
--
-- 3. Concurrency caveat (know it, even if it doesn't bite us):
--    Unlike ON CONFLICT, MERGE is not race-condition-proof under
--    concurrent writers. Our pipeline is a single daily writer, so the
--    trade-off is safe — and being able to articulate this is the point.

MERGE INTO raw.esios_indicator_values AS target
USING tmp_indicator_values AS source
    ON  target.indicator_id = source.indicator_id
    AND target.datetime_utc = source.datetime_utc
    AND target.geo_id       = source.geo_id
WHEN MATCHED AND target.value IS DISTINCT FROM source.value THEN
    UPDATE SET
        value      = source.value,
        updated_at = now()
WHEN NOT MATCHED THEN
    INSERT (indicator_id, datetime_utc, geo_id, value)
    VALUES (source.indicator_id, source.datetime_utc, source.geo_id, source.value);
