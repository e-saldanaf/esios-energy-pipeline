with daily as (

    select * from {{ ref('mart_daily_summary') }}

),

monthly as (

    select
        date_trunc('month', date_utc)                   as month_utc,
        year,
        month,

        -- Generation totals by technology (MWh)
        round(sum(wind_mwh)::numeric, 0)                as wind_mwh,
        round(sum(solar_pv_mwh)::numeric, 0)            as solar_pv_mwh,
        round(sum(hydro_mwh)::numeric, 0)               as hydro_mwh,
        round(sum(coal_mwh)::numeric, 0)                as coal_mwh,
        round(sum(combined_cycle_mwh)::numeric, 0)      as combined_cycle_mwh,
        round(sum(cogen_residues_mwh)::numeric, 0)      as cogen_residues_mwh,
        round(sum(total_mwh)::numeric, 0)               as total_mwh,
        round(sum(renewable_mwh)::numeric, 0)           as renewable_mwh,

        -- Monthly averages
        round(avg(avg_price_eur_mwh)::numeric, 2)       as avg_price_eur_mwh,
        round(avg(renewable_pct)::numeric, 1)           as avg_renewable_pct,

        -- Shares by technology (% of total)
        round(100.0 * sum(wind_mwh)
            / nullif(sum(total_mwh), 0), 1)             as wind_pct,
        round(100.0 * sum(solar_pv_mwh)
            / nullif(sum(total_mwh), 0), 1)             as solar_pv_pct,
        round(100.0 * sum(hydro_mwh)
            / nullif(sum(total_mwh), 0), 1)             as hydro_pct,
        round(100.0 * sum(coal_mwh)
            / nullif(sum(total_mwh), 0), 1)             as coal_pct,
        round(100.0 * sum(combined_cycle_mwh)
            / nullif(sum(total_mwh), 0), 1)             as combined_cycle_pct,
        round(100.0 * sum(cogen_residues_mwh)
            / nullif(sum(total_mwh), 0), 1)             as cogen_residues_pct,

        -- Negative price days in the month
        sum(negative_price_hours)                       as total_negative_price_hours,
        count(case when negative_price_hours > 0
            then 1 end)                                 as negative_price_days

    from daily
    group by date_trunc('month', date_utc), year, month

)

select * from monthly
order by month_utc