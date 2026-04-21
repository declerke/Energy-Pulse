from datetime import datetime, timezone
from typing import Any

from pymongo import MongoClient, UpdateOne
from pymongo.collection import Collection

from app.utils.constants import COLLECTIONS, PRODUCT_QUERIES
from app.utils.logger import get_logger
from config.settings import DATABASE_NAME, MONGODB_URI

logger = get_logger(__name__)


def _client() -> MongoClient:
    return MongoClient(MONGODB_URI)


def _db(client: MongoClient):
    return client[DATABASE_NAME]


def _ensure_indexes(db) -> None:
    db[COLLECTIONS["raw"]].create_index("batch_id")
    db[COLLECTIONS["raw"]].create_index("ingestion_timestamp")

    for product_type, meta in PRODUCT_QUERIES.items():
        col = db[meta["collection"]]
        col.create_index([("country", 1), ("reporting_date", -1), ("product_type", 1)])
        col.create_index("batch_id")

    db[COLLECTIONS["staging"]].create_index("batch_id")
    db[COLLECTIONS["pipeline_runs"]].create_index([("batch_id", 1), ("created_at", -1)])
    db[COLLECTIONS["quality_checks"]].create_index([("batch_id", 1), ("checked_at", -1)])


def write_raw(batch_id: str, records: list[dict]) -> int:
    if not records:
        return 0
    client = _client()
    try:
        db = _db(client)
        _ensure_indexes(db)
        result = db[COLLECTIONS["raw"]].insert_many(records, ordered=False)
        count = len(result.inserted_ids)
        logger.info("Raw: inserted %d records (batch=%s)", count, batch_id)
        return count
    finally:
        client.close()


def write_pipeline_run(batch_id: str, status: str, meta: dict | None = None) -> None:
    client = _client()
    try:
        db = _db(client)
        doc = {
            "batch_id": batch_id,
            "status": status,
            "created_at": datetime.now(timezone.utc).isoformat(),
            **(meta or {}),
        }
        db[COLLECTIONS["pipeline_runs"]].insert_one(doc)
        logger.info("Pipeline run logged: batch=%s status=%s", batch_id, status)
    finally:
        client.close()


def write_quality_check(batch_id: str, result: dict) -> None:
    client = _client()
    try:
        db = _db(client)
        db[COLLECTIONS["quality_checks"]].insert_one({"batch_id": batch_id, **result})
        logger.info("Quality check stored: batch=%s valid=%d invalid=%d",
                    batch_id, result["valid_count"], result["invalid_count"])
    finally:
        client.close()


def write_staging(batch_id: str, records: list[dict]) -> int:
    if not records:
        return 0
    client = _client()
    try:
        db = _db(client)
        result = db[COLLECTIONS["staging"]].insert_many(records, ordered=False)
        count = len(result.inserted_ids)
        logger.info("Staging: inserted %d normalized records (batch=%s)", count, batch_id)
        return count
    finally:
        client.close()


def load_staging(batch_id: str) -> list[dict]:
    client = _client()
    try:
        db = _db(client)
        docs = list(db[COLLECTIONS["staging"]].find({"batch_id": batch_id}, {"_id": 0}))
        return docs
    finally:
        client.close()


def upsert_curated(records: list[dict]) -> dict[str, int]:
    if not records:
        return {}
    client = _client()
    counts: dict[str, int] = {}
    try:
        db = _db(client)
        buckets: dict[str, list[dict]] = {}
        for rec in records:
            pt = rec["product_type"]
            col_name = PRODUCT_QUERIES[pt]["collection"]
            buckets.setdefault(col_name, []).append(rec)

        for col_name, recs in buckets.items():
            ops = [
                UpdateOne(
                    {
                        "country": r["country"],
                        "product_type": r["product_type"],
                        "reporting_date": r["reporting_date"],
                        "unit": r["unit"],
                        "source": r["source"],
                    },
                    {"$set": r},
                    upsert=True,
                )
                for r in recs
            ]
            result = db[col_name].bulk_write(ops, ordered=False)
            counts[col_name] = result.upserted_count + result.modified_count
            logger.info("Curated upsert: %s → %d ops", col_name, counts[col_name])
    finally:
        client.close()
    return counts


def drop_staging(batch_id: str) -> None:
    client = _client()
    try:
        db = _db(client)
        db[COLLECTIONS["staging"]].delete_many({"batch_id": batch_id})
        logger.info("Staging cleared for batch=%s", batch_id)
    finally:
        client.close()


def get_raw_by_batch(batch_id: str) -> list[dict]:
    client = _client()
    try:
        db = _db(client)
        return list(db[COLLECTIONS["raw"]].find({"batch_id": batch_id}, {"_id": 0}))
    finally:
        client.close()
