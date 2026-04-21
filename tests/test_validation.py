import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.validation.validator import validate


def _make_raw(**kwargs):
    base = {
        "batch_id": "test-batch",
        "product_type": "fuel",
        "country": "Germany",
        "country_id": "DEU",
        "period": "2023",
        "raw_value": "6.35",
        "unit": "U.S. Dollars per Gallon",
        "source": "EIA International Energy Statistics",
        "ingestion_timestamp": "2026-04-21T00:00:00+00:00",
    }
    base.update(kwargs)
    return base


def test_validate_clean_records():
    records = [_make_raw(), _make_raw(country="Kenya", raw_value="1.42")]
    result = validate(records)
    assert result["valid_count"] == 2
    assert result["invalid_count"] == 0


def test_validate_catches_null_country():
    result = validate([_make_raw(country="")])
    assert result["invalid_count"] == 1
    assert result["error_breakdown"]["null_field"] == 1


def test_validate_catches_non_numeric_price():
    result = validate([_make_raw(raw_value="N/A")])
    assert result["error_breakdown"]["non_numeric_price"] >= 1


def test_validate_catches_negative_price():
    result = validate([_make_raw(raw_value="-1.5")])
    assert result["error_breakdown"]["negative_price"] == 1


def test_validate_catches_duplicate():
    rec = _make_raw()
    result = validate([rec, rec])
    assert result["error_breakdown"]["duplicate"] == 1


def test_validate_catches_invalid_date():
    result = validate([_make_raw(period="not-a-date")])
    assert result["error_breakdown"]["invalid_date"] == 1


def test_validate_returns_structured_result():
    result = validate([_make_raw()])
    assert "total_records" in result
    assert "valid_count" in result
    assert "invalid_count" in result
    assert "error_breakdown" in result
    assert "sample_failures" in result
    assert "checked_at" in result
