with source as (
    select * from {{ source('esios_raw', 'esios_indicator_values') }}
),
filtered as (
    select
        datetime_utc,
        value as price_eur_mwh
    from source
    where indicator_id = 600 -- Precio Spot (€/MWh)
      and geo_id       = 3 -- Solo España
      and value        is not null  -- Exclude nulls
)
select * from filtered