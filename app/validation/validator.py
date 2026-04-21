from datetime import datetime, timezone
from typing import Any

from app.utils.logger import get_logger

logger = get_logger(__name__)

_REQUIRED_FIELDS = ["country", "product_type", "raw_value", "period", "unit"]


def _check_nulls(record: dict) -> list[str]:
    return [f for f in _REQUIRED_FIELDS if not record.get(f)]


def _check_numeric(record: dict) -> bool:
    raw = record.get("raw_value")
    if raw is None or str(raw).strip() in ("", "-", "NA", "N/A"):
        return False
    try:
        float(raw)
        return True
    except (ValueError, TypeError):
        return False


def _check_negative(record: dict) -> bool:
    raw = record.get("raw_value")
    try:
        return float(raw) < 0
    except (ValueError, TypeError):
        return False


def _check_date(record: dict) -> bool:
    period = record.get("period", "")
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            datetime.strptime(str(period), fmt)
            return True
        except (ValueError, TypeError):
            continue
    return False


def _business_key(record: dict) -> str:
    return "|".join([
        str(record.get("country", "")),
        str(record.get("product_type", "")),
        str(record.get("period", "")),
        str(record.get("unit", "")),
        str(record.get("source", "")),
    ])


def validate(raw_records: list[dict]) -> dict[str, Any]:
    seen_keys: set[str] = set()
    valid: list[dict] = []
    invalid: list[dict] = []
    errors: dict[str, int] = {
        "null_field": 0,
        "non_numeric_price": 0,
        "negative_price": 0,
        "invalid_date": 0,
        "duplicate": 0,
    }
    sample_failures: list[dict] = []

    for rec in raw_records:
        record_errors: list[str] = []

        nulls = _check_nulls(rec)
        if nulls:
            errors["null_field"] += 1
            record_errors.append(f"null_fields:{nulls}")

        if not _check_numeric(rec):
            errors["non_numeric_price"] += 1
            record_errors.append("non_numeric_price")

        if _check_negative(rec):
            errors["negative_price"] += 1
            record_errors.append("negative_price")

        if not _check_date(rec):
            errors["invalid_date"] += 1
            record_errors.append("invalid_date")

        key = _business_key(rec)
        if key in seen_keys:
            errors["duplicate"] += 1
            record_errors.append("duplicate")
        else:
            seen_keys.add(key)

        if record_errors:
            invalid.append(rec)
            if len(sample_failures) < 10:
                sample_failures.append({
                    "country": rec.get("country"),
                    "product_type": rec.get("product_type"),
                    "period": rec.get("period"),
                    "errors": record_errors,
                })
        else:
            valid.append(rec)

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(raw_records),
        "valid_count": len(valid),
        "invalid_count": len(invalid),
        "error_breakdown": errors,
        "sample_failures": sample_failures,
    }

    logger.info(
        "Validation: %d total, %d valid, %d invalid | errors: %s",
        result["total_records"], result["valid_count"],
        result["invalid_count"], errors,
    )
    return result
