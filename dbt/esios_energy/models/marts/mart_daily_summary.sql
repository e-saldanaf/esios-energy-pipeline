with hourly as (

    select * from {{ ref('fct_hourly_market') }}

),

daily as (

    select
        date_utc,
        extract(year  from date_utc)::int               as year,
        extract(month from date_utc)::int               as month,
        extract(dow   from date_utc)::int               as day_of_week,

        -- Price stats
        round(avg(price_eur_mwh)::numeric, 2)           as avg_price_eur_mwh,
        round(min(price_eur_mwh)::numeric, 2)           as min_price_eur_mwh,
        round(max(price_eur_mwh)::numeric, 2)           as max_price_eur_mwh,

        -- Generation totals (MWh)
        round(sum(wind_mwh)::numeric, 0)                as wind_mwh,
        round(sum(solar_pv_mwh)::numeric, 0)            as solar_pv_mwh,
        round(sum(hydro_mwh)::numeric, 0)               as hydro_mwh,
        round(sum(coal_mwh)::numeric, 0)                as coal_mwh,
        round(sum(combined_cycle_mwh)::numeric, 0)      as combined_cycle_mwh,
        round(sum(cogen_residues_mwh)::numeric, 0)      as cogen_residues_mwh,
        round(sum(total_mwh)::numeric, 0)               as total_mwh,
        round(sum(renewable_mwh)::numeric, 0)           as renewable_mwh,

        -- Renewable share for the day
        round(
            100.0 * sum(renewable_mwh) / nullif(sum(total_mwh), 0),
            1
        )                                               as renewable_pct,

        -- Hours with negative price (solar curtailment signal)
        count(case when price_eur_mwh < 0 then 1 end)  as negative_price_hours,

        -- Price volatility
        round(
            (max(price_eur_mwh) - min(price_eur_mwh))::numeric,
            2
        )                                               as price_range_eur_mwh

    from hourly
    group by date_utc

)

select * from daily