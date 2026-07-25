with market as (

    select * from {{ ref('int_hourly_market') }}

),

final as (

    select
        -- Time dimensions
        hour_utc,
        hour_utc at time zone 'Europe/Madrid'           as hour_madrid,
        date_trunc('day', hour_utc)                     as date_utc,
        extract(hour from hour_utc at time zone 'Europe/Madrid')::int
                                                        as hour_of_day,
        extract(dow from hour_utc at time zone 'Europe/Madrid')::int
                                                        as day_of_week,
        extract(month from hour_utc at time zone 'Europe/Madrid')::int
                                                        as month,
        extract(year from hour_utc at time zone 'Europe/Madrid')::int
                                                        as year,

        -- Price
        price_eur_mwh,

        -- Generation by technology (MWh)
        wind_mwh,
        solar_pv_mwh,
        hydro_mwh,
        coal_mwh,
        combined_cycle_mwh,
        cogen_residues_mwh,
        total_mwh,

        -- Derived metrics
        renewable_mwh,
        renewable_pct

    from market
    where price_eur_mwh is not null
      and total_mwh     is not null

)

select * from final