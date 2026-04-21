import sys
sys.path.insert(0, "/opt/airflow")

from datetime import datetime, timedelta

from airflow.sdk import dag, task


@dag(
    dag_id="energy_pipeline",
    start_date=datetime(2026, 4, 1),
    schedule="@daily",
    catchup=False,
    default_args={
        "retries": 3,
        "retry_delay": timedelta(minutes=5),
    },
    tags=["energy", "eia", "global"],
    description="EIA international energy price ingestion, validation, transformation, and reporting",
)
def energy_pipeline():

    @task()
    def ingest_data() -> str:
        from app.ingestion.eia_client import fetch_all
        from app.loaders.mongo_loader import write_raw, write_pipeline_run

        batch_id, records = fetch_all()
        write_raw(batch_id, records)
        write_pipeline_run(batch_id, "ingested", {"raw_records": len(records)})
        return batch_id

    @task()
    def validate_data(batch_id: str) -> str:
        from app.loaders.mongo_loader import get_raw_by_batch, write_quality_check
        from app.validation.validator import validate

        raw_records = get_raw_by_batch(batch_id)
        result = validate(raw_records)
        write_quality_check(batch_id, result)
        return batch_id

    @task()
    def transform_data(batch_id: str) -> str:
        from app.loaders.mongo_loader import get_raw_by_batch, write_staging
        from app.transformation.normalizer import normalize

        raw_records = get_raw_by_batch(batch_id)
        normalized = normalize(raw_records)
        write_staging(batch_id, normalized)
        return batch_id

    @task()
    def load_to_mongodb(batch_id: str) -> str:
        from app.loaders.mongo_loader import drop_staging, load_staging, upsert_curated, write_pipeline_run

        staged = load_staging(batch_id)
        counts = upsert_curated(staged)
        drop_staging(batch_id)
        write_pipeline_run(batch_id, "loaded", {"curated_counts": counts})
        return batch_id

    @task()
    def generate_report(batch_id: str) -> None:
        from app.loaders.mongo_loader import write_pipeline_run
        from app.services.reporting import build_report

        report = build_report(batch_id)
        write_pipeline_run(batch_id, "completed", {
            "report_summary": {
                "processed": report["processed_records"],
                "invalid": report["invalid_records"],
                "top_increase_count": len(report["top_increase"]),
                "top_decrease_count": len(report["top_decrease"]),
            }
        })

    batch = ingest_data()
    validated = validate_data(batch)
    transformed = transform_data(validated)
    loaded = load_to_mongodb(transformed)
    generate_report(loaded)


energy_pipeline()
