import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import patch

import pytest

from flask_app.app import create_app


@pytest.fixture()
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def test_health_endpoint(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["status"] == "ok"


def test_prices_endpoint_returns_json(client):
    mock_prices = [
        {"country": "Germany", "product_type": "fuel", "price": 6.35,
         "currency": "USD", "unit": "per gallon", "reporting_date": "2023-12-31"}
    ]
    with patch("flask_app.routes.api.latest_prices", return_value=mock_prices):
        resp = client.get("/api/prices")
    assert resp.status_code == 200
    data = resp.get_json()
    assert "records" in data
    assert data["count"] == 1


def test_prices_endpoint_empty(client):
    with patch("flask_app.routes.api.latest_prices", return_value=[]):
        resp = client.get("/api/prices")
    assert resp.status_code == 200
    assert resp.get_json()["count"] == 0


def test_report_endpoint_no_runs(client):
    mock_summary = {"latest_run": {"batch_id": None, "status": "no_runs",
                                    "created_at": None, "raw_records": 0}, "quality": {}}
    with patch("flask_app.routes.api.pipeline_summary", return_value=mock_summary):
        resp = client.get("/api/report")
    assert resp.status_code == 404


def test_report_endpoint_with_run(client):
    mock_summary = {"latest_run": {"batch_id": "abc-123", "status": "completed",
                                    "created_at": "2026-04-21T00:00:00Z", "raw_records": 500}, "quality": {}}
    mock_report = {
        "generated_at": "2026-04-21T00:00:00Z",
        "batch_id": "abc-123",
        "processed_records": 500,
        "invalid_records": 10,
        "top_increase": [],
        "top_decrease": [],
        "pipeline_status": "completed",
    }
    with patch("flask_app.routes.api.pipeline_summary", return_value=mock_summary), \
         patch("flask_app.routes.api.build_report", return_value=mock_report):
        resp = client.get("/api/report")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["batch_id"] == "abc-123"
    assert data["processed_records"] == 500
