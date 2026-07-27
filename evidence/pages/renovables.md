---
title: Impacto Renovable
---

# Impacto de las Renovables en el Precio

El **merit order effect**: cuando hay más generación renovable (coste marginal cero),
las plantas térmicas caras son desplazadas de la curva de oferta, reduciendo el precio de casación.

```sql renovables_vs_precio
select
    date_utc,
    avg_price_eur_mwh,
    renewable_pct,
    wind_mwh,
    solar_pv_mwh,
    hydro_mwh,
    renewable_bucket,
    price_bucket,
    had_negative_prices,
    high_renewable_day
from supabase.mart_renewables_price_impact
order by date_utc
```

```sql precio_por_bucket_renovable
select
    renewable_bucket,
    round(avg(avg_price_eur_mwh)::numeric, 2) as avg_price,
    count(*) as dias
from supabase.mart_renewables_price_impact
group by renewable_bucket
order by renewable_bucket
```

```sql dias_precio_negativo
select
    date_utc,
    avg_price_eur_mwh,
    renewable_pct,
    had_negative_prices
from supabase.mart_renewables_price_impact
where had_negative_prices = true
order by date_utc
```

## Precio medio por nivel de generación renovable

<BarChart
    data={precio_por_bucket_renovable}
    x=renewable_bucket
    y=avg_price
    title="Precio medio (€/MWh) según % renovable"
    yAxisTitle="€/MWh"
/>

## Precio diario vs % Renovable

<ScatterPlot
    data={renovables_vs_precio}
    x=renewable_pct
    y=avg_price_eur_mwh
    title="Merit Order Effect — precio vs % renovable"
    xAxisTitle="% Generación renovable"
    yAxisTitle="Precio (€/MWh)"
    xFmt="0.0"
/>

## Días con precio negativo

<BarChart
    data={dias_precio_negativo}
    x=date_utc
    y=avg_price_eur_mwh
    title="Días con alguna hora de precio negativo"
    yAxisTitle="€/MWh"
/>