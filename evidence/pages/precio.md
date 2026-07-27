---
title: Precio Spot
---

# Precio Spot del Mercado Eléctrico Español

```sql precio_diario
select
    date_utc,
    avg_price_eur_mwh,
    min_price_eur_mwh,
    max_price_eur_mwh,
    negative_price_hours,
    renewable_pct
from supabase.mart_daily_summary
order by date_utc
```

```sql precio_horario_heatmap
select
    hour_of_day,
    day_of_week,
    avg(price_eur_mwh) as avg_price
from supabase.fct_hourly_market
group by hour_of_day, day_of_week
order by day_of_week, hour_of_day
```

```sql precio_mensual
select
    date_trunc('month', date_utc) as month_utc,
    avg(avg_price_eur_mwh) as avg_price,
    avg(renewable_pct) as avg_renewable_pct
from supabase.mart_daily_summary
group by 1
order by 1
```

## Evolución del precio diario

<LineChart
    data={precio_diario}
    x=date_utc
    y=avg_price_eur_mwh
    title="Precio medio diario (€/MWh)"
    yAxisTitle="€/MWh"
/>

## Precio medio mensual vs % Renovable

<LineChart
    data={precio_mensual}
    x=month_utc
    y={["avg_price", "avg_renewable_pct"]}
    title="Precio mensual y % Renovable"
/>

## Horas con precio negativo

<BarChart
    data={precio_diario}
    x=date_utc
    y=negative_price_hours
    title="Horas con precio negativo por día"
    yAxisTitle="Horas"
/>