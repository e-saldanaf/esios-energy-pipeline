"""Discovery script: find ESIOS indicator ids for config.INDICATORS.

Usage:
    python -m scripts.discover_indicators generación
    python -m scripts.discover_indicators demanda
    python -m scripts.discover_indicators            # full catalogue

DIDACTIC NOTE — Why a discovery script instead of hardcoding ids from a
blog post: public API catalogues drift. Ids get deprecated, renamed or
split. Verifying against the LIVE catalogue with your own token is the
only source of truth — and it doubles as a token smoke test.

Once you have the candidates, sanity-check each one by pulling a single
day of data and eyeballing the granularity (hourly?) and units (MWh? %?):

    from datetime import datetime, timezone
    from extract.esios_client import EsiosClient
    c = EsiosClient()
    rows = c.get_indicator_values(
        1433,
        datetime(2026, 7, 1, tzinfo=timezone.utc),
        datetime(2026, 7, 2, tzinfo=timezone.utc),
    )
    print(len(rows), rows[:2])

Expected for hourly data: 24-25 rows (25 on DST-change days — knowing that
off the top of your head is an interview flex).
"""

import sys

from extract.esios_client import EsiosClient


def main() -> None:
    text_filter = sys.argv[1] if len(sys.argv) > 1 else None
    client = EsiosClient()
    indicators = client.list_indicators(text_filter)
    print(f"{'ID':>6}  NAME")
    print("-" * 80)
    for ind in sorted(indicators, key=lambda i: i["id"]):
        print(f"{ind['id']:>6}  {ind['name']}")
    print(f"\n{len(indicators)} indicators matched.")


if __name__ == "__main__":
    main()