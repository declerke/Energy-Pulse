import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.transformation.normalizer import normalize


def _make_raw(country="Germany", period="2023", value="6.35", product_type="fuel"):
    return {
        "batch_id": "test-batch",
        "product_type": product_type,
        "country": country,
        "country_id": "DEU",
        "period": period,
        "raw_value": value,
        "unit": "U.S. Dollars per Gallon",
        "activity": "Price",
        "product_name": "Motor Gasoline",
        "source": "EIA International Energy Statistics",
        "ingestion_timestamp": "2026-04-21T00:00:00+00:00",
    }


def test_normalize_valid_record():
    result = normalize([_make_raw()])
    assert len(result) == 1
    r = result[0]
    assert r["country"] == "Germany"
    assert r["price"] == 6.35
    assert r["currency"] == "USD"
    assert r["reporting_date"] == "2023-12-31"


def test_normalize_monthly_period():
    result = normalize([_make_raw(period="2023-06")])
    assert result[0]["reporting_date"] == "2023-06-01"


def test_normalize_daily_period():
    result = normalize([_make_raw(period="2026-04-10")])
    assert result[0]["reporting_date"] == "2026-04-10"


def test_normalize_skips_null_value():
    result = normalize([_make_raw(value=None)])
    assert result == []


def test_normalize_skips_dash_value():
    result = normalize([_make_raw(value="-")])
    assert result == []


def test_normalize_skips_invalid_period():
    result = normalize([_make_raw(period="not-a-date")])
    assert result == []


def test_normalize_multiple_records():
    records = [_make_raw("Germany", "2023"), _make_raw("Kenya", "2022"), _make_raw("USA", None)]
    result = normalize(records)
    assert len(result) == 2
