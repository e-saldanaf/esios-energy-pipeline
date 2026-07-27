---
title: Mix Tecnológico
---

# Mix de Generación por Tecnología

```sql mix_mensual
select
    month_utc,
    wind_pct,
    solar_pv_pct,
    hydro_pct,
    coal_pct,
    combined_cycle_pct,
    cogen_residues_pct,
    avg_renewable_pct,
    avg_price_eur_mwh,
    negative_price_days
from supabase.mart_technology_mix
order by month_utc
```

```sql mix_total
select
    month_utc,
    wind_mwh,
    solar_pv_mwh,
    hydro_mwh,
    coal_mwh,
    combined_cycle_mwh,
    cogen_residues_mwh
from supabase.mart_technology_mix
order by month_utc
```

## Evolución del mix renovable

<LineChart
    data={mix_mensual}
    x=month_utc
    y={["wind_pct", "solar_pv_pct", "hydro_pct"]}
    title="Generación renovable por tecnología (%)"
    yAxisTitle="%"
    yFmt="0.0"
/>

## Evolución del mix fósil

<LineChart
    data={mix_mensual}
    x=month_utc
    y={["coal_pct", "combined_cycle_pct"]}
    title="Generación fósil por tecnología (%)"
    yAxisTitle="%"
    yFmt="0.0"
/>

## Generación total por tecnología (MWh)

<BarChart
    data={mix_total}
    x=month_utc
    y={["wind_mwh", "solar_pv_mwh", "hydro_mwh", "coal_mwh", "combined_cycle_mwh", "cogen_residues_mwh"]}
    title="Generación mensual por tecnología (MWh)"
    yAxisTitle="MWh"
    type=stacked
/>

## Días con precio negativo por mes

<BarChart
    data={mix_mensual}
    x=month_utc
    y=negative_price_days
    title="Días con precio negativo por mes"
    yAxisTitle="Días"
/>