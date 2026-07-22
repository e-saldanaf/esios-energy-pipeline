"""ESIOS (REE) API client.

Extractor layer: ONLY fetches raw data. No transformation, no DB access
(Clean Architecture — each layer has one reason to change).

DIDACTIC NOTE — Retry strategy:
    Public APIs fail transiently (5xx, timeouts, rate limits). Retrying
    with exponential backoff turns most of those into non-events. We retry
    ONLY on retryable statuses — retrying a 401 (bad token) or 404 (bad
    indicator id) just delays the real error message.
"""

from datetime import datetime
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from extract.config import settings
from extract.logging_setup import get_logger

logger = get_logger("esios_client")

RETRYABLE_STATUSES = (429, 500, 502, 503, 504)


class EsiosClient:
    def __init__(self) -> None:
        self.session = requests.Session()
        retry = Retry(
            total=4,
            backoff_factor=2,  # 2s, 4s, 8s, 16s
            status_forcelist=RETRYABLE_STATUSES,
            allowed_methods=("GET",),
        )
        self.session.mount("https://", HTTPAdapter(max_retries=retry))
        self.session.headers.update(
            {
                "Accept": "application/json; application/vnd.esios-api-v1+json",
                "Content-Type": "application/json",
                "x-api-key": settings.esios_api_token,
            }
        )

    def get_indicator_values(
        self, indicator_id: int, start_utc: datetime, end_utc: datetime
    ) -> list[dict[str, Any]]:
        """Fetch raw indicator values for a UTC window.

        Returns the raw `values` list untouched — normalisation is the
        loader/transform's job, not the extractor's.
        """
        url = f"{settings.esios_base_url}/indicators/{indicator_id}"
        params = {
            "start_date": start_utc.isoformat(),
            "end_date": end_utc.isoformat(),
        }
        logger.info(
            "fetching_indicator",
            extra={"ctx": {"indicator_id": indicator_id, "start": start_utc, "end": end_utc}},
        )
        response = self.session.get(url, params=params, timeout=120)
        response.raise_for_status()
        values = response.json().get("indicator", {}).get("values", [])
        logger.info(
            "fetched_indicator",
            extra={"ctx": {"indicator_id": indicator_id, "rows": len(values)}},
        )
        return values

    def list_indicators(self, text_filter: str | None = None) -> list[dict[str, Any]]:
        """Discovery helper: browse the live indicator catalogue.

        DIDACTIC NOTE — Use this (not blog posts) to confirm the generation
        indicator ids for config.INDICATORS. APIs drift; catalogues don't lie.
        """
        response = self.session.get(f"{settings.esios_base_url}/indicators", timeout=120
        response.raise_for_status()
        indicators = response.json().get("indicators", [])
        if text_filter:
            needle = text_filter.lower()
            indicators = [i for i in indicators if needle in i.get("name", "").lower()]
        return indicators
