with prices as (

    select * from {{ ref('stg_esios__hourly_prices') }}

),

generation as (

    select * from {{ ref('stg_esios__generation') }}

),

technologies as (

    select * from {{ ref('stg_esios__technologies') }}

),

joined as (

    select
        -- Time dimension
        prices.hour_utc,

        -- Price
        prices.price_eur_mwh,

        -- Generation by technology (MWh)
        generation.wind_mwh,
        generation.solar_pv_mwh,
        generation.hydro_mwh,
        generation.coal_mwh,
        generation.combined_cycle_mwh,
        generation.cogen_residues_mwh,
        generation.total_mwh,

        -- Derived renewable metrics
        coalesce(generation.wind_mwh, 0)
            + coalesce(generation.solar_pv_mwh, 0)
            + coalesce(generation.hydro_mwh, 0)            as renewable_mwh,

        -- Renewable share (0-100)
        case
            when generation.total_mwh > 0
            then round(
                100.0 * (
                    coalesce(generation.wind_mwh, 0)
                    + coalesce(generation.solar_pv_mwh, 0)
                    + coalesce(generation.hydro_mwh, 0)
                ) / generation.total_mwh,
                1
            )
            else null
        end                                                 as renewable_pct

    from prices
    left join generation
    on prices.hour_utc = generation.hour_utc

)

select * from joined