import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import MagicMock, patch

from app.ingestion.eia_client import _fetch_endpoint


MOCK_RESPONSE = {
    "response": {
        "total": 2,
        "data": [
            {
                "period": "2026-04-10",
                "series": "RWTC",
                "series-description": "Cushing, OK WTI Spot Price FOB (Dollars per Barrel)",
                "product-name": "WTI Crude Oil",
                "process-name": "Spot Price FOB",
                "value": "62.35",
                "units": "$/BBL",
            },
            {
                "period": "2026-04-10",
                "series": "RBRTE",
                "series-description": "Europe Brent Spot Price FOB (Dollars per Barrel)",
                "product-name": "UK Brent Crude Oil",
                "process-name": "Spot Price FOB",
                "value": "66.12",
                "units": "$/BBL",
            },
        ],
    }
}


def test_fetch_endpoint_returns_records():
    mock_resp = MagicMock()
    mock_resp.json.return_value = MOCK_RESPONSE
    mock_resp.raise_for_status.return_value = None

    with patch("app.ingestion.eia_client.requests.get", return_value=mock_resp):
        records = _fetch_endpoint("fuel", "test-batch-001")

    assert len(records) == 2
    assert records[0]["country_id"] == "RWTC"
    assert records[1]["country_id"] == "RBRTE"
    assert records[0]["product_type"] == "fuel"
    assert records[0]["batch_id"] == "test-batch-001"
    assert records[0]["raw_value"] == "62.35"
    assert records[0]["unit"] == "$/BBL"


def test_fetch_endpoint_handles_empty_response():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"response": {"total": 0, "data": []}}
    mock_resp.raise_for_status.return_value = None

    with patch("app.ingestion.eia_client.requests.get", return_value=mock_resp):
        records = _fetch_endpoint("fuel", "test-batch-002")

    assert records == []


def test_fetch_endpoint_handles_api_error():
    import requests as req_lib
    with patch("app.ingestion.eia_client.requests.get", side_effect=req_lib.RequestException("timeout")):
        records = _fetch_endpoint("fuel", "test-batch-003")

    assert records == []
