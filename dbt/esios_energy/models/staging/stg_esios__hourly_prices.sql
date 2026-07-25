with source as (

    select * from {{ source('esios_raw', 'esios_indicator_values') }}

),

filtered as (

    select
        date_trunc('hour', datetime_utc)    as hour_utc,
        avg(value)                          as price_eur_mwh

    from source

    where indicator_id = 600
      and geo_id       = 3
      and value        is not null

    group by date_trunc('hour', datetime_utc)

)

select * from filtered