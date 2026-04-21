import uuid
from datetime import datetime, timezone
from typing import Any

import requests

from app.utils.constants import PRODUCT_QUERIES, SOURCE
from app.utils.logger import get_logger
from config.settings import EIA_API_KEY, EIA_BASE_URL

logger = get_logger(__name__)

_PAGE_SIZE = 5000

_ENDPOINTS = {
    "fuel": f"{EIA_BASE_URL}/petroleum/pri/spt/data/",
    "natural_gas": f"{EIA_BASE_URL}/natural-gas/pri/fut/data/",
}


def _fetch_endpoint(product_type: str, batch_id: str) -> list[dict[str, Any]]:
    url = _ENDPOINTS[product_type]
    records: list[dict] = []
    offset = 0
    ingestion_ts = datetime.now(timezone.utc).isoformat()

    while True:
        params = {
            "api_key": EIA_API_KEY,
            "data[]": "value",
            "sort[0][column]": "period",
            "sort[0][direction]": "desc",
            "length": _PAGE_SIZE,
            "offset": offset,
        }
        try:
            resp = requests.get(url, params=params, timeout=30)
            resp.raise_for_status()
        except requests.RequestException as exc:
            logger.error("EIA API request failed for %s: %s", product_type, exc)
            break

        payload = resp.json().get("response", {})
        page_data = payload.get("data", [])
        if not page_data:
            break

        for row in page_data:
            records.append({
                "batch_id": batch_id,
                "product_type": product_type,
                "country": row.get("series-description", ""),
                "country_id": row.get("series", ""),
                "period": row.get("period"),
                "raw_value": row.get("value"),
                "unit": row.get("units", ""),
                "activity": row.get("process-name", "Spot Price"),
                "product_name": row.get("product-name", ""),
                "source": SOURCE,
                "ingestion_timestamp": ingestion_ts,
            })

        total = int(payload.get("total", 0))
        offset += len(page_data)
        logger.info("Fetched %d/%d records for %s (offset=%d)", len(records), total, product_type, offset)
        if offset >= total:
            break

    return records


def fetch_all(batch_id: str | None = None) -> tuple[str, list[dict]]:
    if batch_id is None:
        batch_id = str(uuid.uuid4())

    all_records: list[dict] = []
    for product_type in PRODUCT_QUERIES:
        logger.info("Fetching %s prices from EIA...", product_type)
        records = _fetch_endpoint(product_type, batch_id)
        all_records.extend(records)
        logger.info("  → %d records retrieved for %s", len(records), product_type)

    logger.info("Total raw records fetched: %d (batch_id=%s)", len(all_records), batch_id)
    return batch_id, all_records
