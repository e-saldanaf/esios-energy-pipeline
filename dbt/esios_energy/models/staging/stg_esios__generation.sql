with source as (
    select * from {{ source('esios_raw', 'esios_indicator_values') }}
),
generation_raw as (
    -- Excluir 10004 (total)
    select
        date_trunc('hour', datetime_utc) as hour_utc,
        indicator_id,
        value
    from source
    where indicator_id in (2038, 2040, 2041, 2042, 2044, 2051) -- Generation indicators
      and geo_id = 3 -- Solo España
),
generation_hourly as (
    -- agregar 6 lecturas por hora por tecnología = 1 valor horario
    select
        hour_utc,
        indicator_id,
        sum(value) as value_mwh
    from generation_raw
    group by hour_utc, indicator_id -- Agrupar por hora y tecnología
),
pivoted as (
    -- Pivotar para que cada tecnología sea una columna
    -- Esto es más eficiente que usar un join por cada tecnología
    select
        hour_utc,
        sum(case when indicator_id = 2038 then value_mwh end) as wind_mwh,
        sum(case when indicator_id = 2040 then value_mwh end) as coal_mwh,
        sum(case when indicator_id = 2041 then value_mwh end) as combined_cycle_mwh,
        sum(case when indicator_id = 2042 then value_mwh end) as hydro_mwh,
        sum(case when indicator_id = 2044 then value_mwh end) as solar_pv_mwh,
        sum(case when indicator_id = 2051 then value_mwh end) as cogen_residues_mwh,
        -- Total derivado de nuestros propios datos, no del indicador 10004 de ESIOS
        sum(value_mwh)                                        as total_mwh
    from generation_hourly
    group by hour_utc
)
select * from pivoted