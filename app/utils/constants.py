COLLECTIONS = {
    "raw": "raw_api_data",
    "fuel": "fuel_prices",
    "natural_gas": "natural_gas_prices",
    "staging": "staging_transformed",
    "pipeline_runs": "pipeline_runs",
    "quality_checks": "data_quality_checks",
}

PRODUCT_QUERIES = {
    "fuel": {
        "collection": COLLECTIONS["fuel"],
    },
    "natural_gas": {
        "collection": COLLECTIONS["natural_gas"],
    },
}

SOURCE = "EIA Energy Statistics"
