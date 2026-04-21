from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient

from app.utils.constants import COLLECTIONS, PRODUCT_QUERIES
from app.utils.logger import get_logger
from config.settings import DATABASE_NAME, MONGODB_URI

logger = get_logger(__name__)


def _client() -> MongoClient:
    return MongoClient(MONGODB_URI)


def _db(client: MongoClient):
    return client[DATABASE_NAME]


def latest_prices(product_type: str | None = None, limit: int = 200) -> list[dict]:
    client = _client()
    try:
        db = _db(client)
        collections = (
            [PRODUCT_QUERIES[product_type]["collection"]]
            if product_type
            else [m["collection"] for m in PRODUCT_QUERIES.values()]
        )
        results: list[dict] = []
        for col_name in collections:
            pipeline = [
                {"$sort": {"reporting_date": -1}},
                {"$group": {
                    "_id": {"country": "$country", "product_type": "$product_type"},
                    "price": {"$first": "$price"},
                    "currency": {"$first": "$currency"},
                    "unit": {"$first": "$unit"},
                    "reporting_date": {"$first": "$reporting_date"},
                    "country": {"$first": "$country"},
                    "product_type": {"$first": "$product_type"},
                }},
                {"$project": {"_id": 0}},
                {"$sort": {"country": 1}},
                {"$limit": limit},
            ]
            results.extend(db[col_name].aggregate(pipeline))
        return results
    finally:
        client.close()


def price_movements(product_type: str | None = None, top_n: int = 5) -> dict[str, list]:
    client = _client()
    try:
        db = _db(client)
        collections = (
            [PRODUCT_QUERIES[product_type]["collection"]]
            if product_type
            else [m["collection"] for m in PRODUCT_QUERIES.values()]
        )
        deltas: list[dict] = []
        for col_name in collections:
            pipeline = [
                {"$sort": {"reporting_date": -1}},
                {"$group": {
                    "_id": {"country": "$country", "product_type": "$product_type"},
                    "prices": {"$push": {"price": "$price", "date": "$reporting_date"}},
                    "country": {"$first": "$country"},
                    "product_type": {"$first": "$product_type"},
                }},
            ]
            for doc in db[col_name].aggregate(pipeline):
                pts = sorted(doc["prices"], key=lambda x: x["date"], reverse=True)
                if len(pts) >= 2:
                    delta = round(pts[0]["price"] - pts[1]["price"], 4)
                    deltas.append({
                        "country": doc["country"],
                        "product_type": doc["product_type"],
                        "current_price": pts[0]["price"],
                        "previous_price": pts[1]["price"],
                        "delta": delta,
                        "current_period": pts[0]["date"],
                        "previous_period": pts[1]["date"],
                    })

        deltas.sort(key=lambda x: x["delta"], reverse=True)
        return {
            "top_increase": deltas[:top_n],
            "top_decrease": deltas[-top_n:][::-1],
        }
    finally:
        client.close()


def pipeline_summary(batch_id: str | None = None) -> dict[str, Any]:
    client = _client()
    try:
        db = _db(client)
        run_filter = {"batch_id": batch_id} if batch_id else {}
        run = db[COLLECTIONS["pipeline_runs"]].find_one(
            run_filter, sort=[("created_at", -1)]
        )
        qc = db[COLLECTIONS["quality_checks"]].find_one(
            run_filter, sort=[("checked_at", -1)]
        )
        return {
            "latest_run": {
                "batch_id": run.get("batch_id") if run else None,
                "status": run.get("status") if run else "no_runs",
                "created_at": run.get("created_at") if run else None,
                "raw_records": run.get("raw_records") if run else 0,
            },
            "quality": {
                "total": qc.get("total_records") if qc else 0,
                "valid": qc.get("valid_count") if qc else 0,
                "invalid": qc.get("invalid_count") if qc else 0,
            } if qc else {},
        }
    finally:
        client.close()


def build_report(batch_id: str) -> dict[str, Any]:
    movements = price_movements()
    summary = pipeline_summary(batch_id)
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "batch_id": batch_id,
        "processed_records": summary["latest_run"].get("raw_records", 0),
        "invalid_records": summary.get("quality", {}).get("invalid", 0),
        "top_increase": movements["top_increase"],
        "top_decrease": movements["top_decrease"],
        "pipeline_status": summary["latest_run"].get("status"),
    }
