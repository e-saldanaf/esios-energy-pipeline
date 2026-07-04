-- Watermark: last loaded timestamp for a given indicator.
--
-- DIDACTIC NOTE — This single query is what makes the pipeline
-- self-healing against unreliable schedulers (GitHub Actions cron skips):
-- every run asks "what do I already have?" and extracts from there.
-- A skipped run becomes latency, never data loss.
--
-- Returns NULL on first run; Python falls back to the backfill start date.

SELECT max(datetime_utc) AS watermark
FROM raw.esios_indicator_values
WHERE indicator_id = %(indicator_id)s;
