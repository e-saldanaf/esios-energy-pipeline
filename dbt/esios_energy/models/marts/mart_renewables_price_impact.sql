with daily as (

    select * from {{ ref('mart_daily_summary') }}

),

final as (

    select
        date_utc,
        year,
        month,

        -- Price
        avg_price_eur_mwh,

        -- Renewable share
        renewable_pct,

        -- Renewable breakdown
        wind_mwh,
        solar_pv_mwh,
        hydro_mwh,
        renewable_mwh,
        total_mwh,

        -- Price buckets for grouping in charts
        case
            when avg_price_eur_mwh < 0   then '< 0 €'
            when avg_price_eur_mwh < 25  then '0-25 €'
            when avg_price_eur_mwh < 50  then '25-50 €'
            when avg_price_eur_mwh < 75  then '50-75 €'
            when avg_price_eur_mwh < 100 then '75-100 €'
            else '> 100 €'
        end                                         as price_bucket,

        -- Renewable share buckets
        case
            when renewable_pct < 20  then '0-20%'
            when renewable_pct < 40  then '20-40%'
            when renewable_pct < 60  then '40-60%'
            when renewable_pct < 80  then '60-80%'
            else '> 80%'
        end                                         as renewable_bucket,

        -- Signal flags
        negative_price_hours > 0                    as had_negative_prices,
        renewable_pct > 70                          as high_renewable_day

    from daily
    where avg_price_eur_mwh is not null
      and renewable_pct     is not null

)

select * from final