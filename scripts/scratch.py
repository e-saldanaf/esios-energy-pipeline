from datetime import datetime, timezone
from extract.esios_client import EsiosClient

client = EsiosClient()


# Confirmar geo_id de España para precio SPOT
rows_600 = client.get_indicator_values(
    600,
    datetime(2026, 6, 1, tzinfo=timezone.utc),
    datetime(2026, 6, 2, tzinfo=timezone.utc),
)
geos = {r['geo_id']: r['geo_name'] for r in rows_600}
print("Geo IDs en precio SPOT:", geos)

# Confirmar geo_id de España en generación eólica nacional
rows_2038 = client.get_indicator_values(
    2038,
    datetime(2026, 6, 1, tzinfo=timezone.utc),
    datetime(2026, 6, 2, tzinfo=timezone.utc),
)
geos_2038 = {r['geo_id']: r['geo_name'] for r in rows_2038}
print("Geo IDs en eólica nacional:", geos_2038)

