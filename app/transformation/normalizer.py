from datetime import datetime, timezone, date
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

_PERIOD_FORMATS = ["%Y-%m-%d", "%Y-%m", "%Y"]


def _parse_period(period: str) -> date | None:
    for fmt in _PERIOD_FORMATS:
        try:
            dt = datetime.strptime(period, fmt)
            if fmt == "%Y":
                return date(dt.year, 12, 31)
            return date(dt.year, dt.month, dt.day if fmt == "%Y-%m-%d" else 1)
        except (ValueError, TypeError):
            continue
    return None


def _parse_price(raw: Any) -> float | None:
    if raw is None or str(raw).strip() in ("", "-", "NA", "N/A"):
        return None
    try:
        return float(raw)
    except (ValueError, TypeError):
        return None


def normalize(raw_records: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    skipped = 0

    for rec in raw_records:
        price = _parse_price(rec.get("raw_value"))
        reporting_date = _parse_period(rec.get("period", ""))

        if price is None or reporting_date is None:
            skipped += 1
            continue

        normalized.append({
            "batch_id": rec["batch_id"],
            "country": (rec.get("country") or "").strip(),
            "country_id": (rec.get("country_id") or "").strip(),
            "product_type": rec["product_type"],
            "price": price,
            "currency": "USD",
            "unit": (rec.get("unit") or "").strip(),
            "reporting_date": reporting_date.isoformat(),
            "source": rec["source"],
            "ingestion_timestamp": rec["ingestion_timestamp"],
            "normalized_at": datetime.now(timezone.utc).isoformat(),
        })

    logger.info(
        "Normalization complete: %d valid, %d skipped",
        len(normalized), skipped,
    )
    return normalized
