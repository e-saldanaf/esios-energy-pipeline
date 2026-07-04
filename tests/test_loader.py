"""Unit tests for the pure transformation function of the loader.

DIDACTIC NOTE — What we test and what we don't (yet):
    `normalise_values` is a pure function: same input, same output, no I/O.
    That makes it cheap to test exhaustively with fixture payloads.
    DB-touching code (MERGE) is integration-test territory — phase CI/CD
    will add a job running it against a disposable Postgres service
    container, which is the honest way to test SQL.
"""

from datetime import timezone

from extract.loader import normalise_values


def test_normalise_parses_utc_timestamps():
    payload = [{"datetime_utc": "2026-01-01T00:00:00Z", "geo_id": 3, "value": 45.2}]
    rows = normalise_values(600, payload)
    assert rows == [(600, rows[0][1], 3, 45.2)]
    assert rows[0][1].tzinfo is not None
    assert rows[0][1].utcoffset().total_seconds() == 0


def test_normalise_defaults_missing_geo_to_zero():
    payload = [{"datetime_utc": "2026-01-01T00:00:00+00:00", "value": 10.0}]
    rows = normalise_values(600, payload)
    assert rows[0][2] == 0


def test_normalise_preserves_null_values():
    # ESIOS can publish nulls; raw must keep them — staging decides policy.
    payload = [{"datetime_utc": "2026-01-01T00:00:00+00:00", "value": None}]
    rows = normalise_values(600, payload)
    assert rows[0][3] is None


def test_normalise_coerces_naive_timestamps_to_utc():
    payload = [{"datetime": "2026-01-01T05:00:00", "value": 1.0}]
    rows = normalise_values(600, payload)
    assert rows[0][1].tzinfo == timezone.utc


def test_normalise_empty_payload_returns_empty_list():
    assert normalise_values(600, []) == []
