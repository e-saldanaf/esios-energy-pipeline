---
title: Mercado Eléctrico Español ⚡
---

Análisis del precio spot y mix de generación en el sistema peninsular español.
Datos: [ESIOS/REE](https://www.esios.ree.es) · Actualización diaria automática.

```sql kpis
select
    round(avg(avg_price_eur_mwh)::numeric, 2)   as precio_medio,
    round(max(max_price_eur_mwh)::numeric, 2)   as precio_max,
    round(min(min_price_eur_mwh)::numeric, 2)   as precio_min,
    round(avg(renewable_pct)::numeric, 1)        as pct_renovable_medio,
    sum(negative_price_hours)                    as horas_precio_negativo
from supabase.mart_daily_summary
where date_utc >= current_date - interval '30 days'
```

<BigValue
    data={kpis}
    value=precio_medio
    title="Precio medio (30d)"
    fmt="0.00"
/>

<BigValue
    data={kpis}
    value=pct_renovable_medio
    title="% Renovable medio (30d)"
    fmt="0.0"
/>

<BigValue
    data={kpis}
    value=horas_precio_negativo
    title="Horas precio negativo (30d)"
/>

---

```sql precio_30d
select
    date_utc,
    avg_price_eur_mwh,
    renewable_pct
from supabase.mart_daily_summary
where date_utc >= current_date - interval '30 days'
order by date_utc
```

## Precio spot — últimos 30 días

<LineChart
    data={precio_30d}
    x=date_utc
    y=avg_price_eur_mwh
    title="Precio medio diario (€/MWh)"
    yAxisTitle="€/MWh"
/>

---

```sql mix_ultimo_mes
select 'Eólica' as tecnologia, wind_pct as porcentaje
from supabase.mart_technology_mix
where month_utc = (select max(month_utc) from supabase.mart_technology_mix)
union all
select 'Solar FV', solar_pv_pct
from supabase.mart_technology_mix
where month_utc = (select max(month_utc) from supabase.mart_technology_mix)
union all
select 'Hidráulica', hydro_pct
from supabase.mart_technology_mix
where month_utc = (select max(month_utc) from supabase.mart_technology_mix)
union all
select 'Carbón', coal_pct
from supabase.mart_technology_mix
where month_utc = (select max(month_utc) from supabase.mart_technology_mix)
union all
select 'Ciclo combinado', combined_cycle_pct
from supabase.mart_technology_mix
where month_utc = (select max(month_utc) from supabase.mart_technology_mix)
union all
select 'Cogeneración', cogen_residues_pct
from supabase.mart_technology_mix
where month_utc = (select max(month_utc) from supabase.mart_technology_mix)
```

## Mix de generación — último mes

<BarChart
    data={mix_ultimo_mes}
    x=tecnologia
    y=porcentaje
    title="Generación por tecnología — último mes (%)"
    yAxisTitle="%"
    yFmt="0.0"
/>