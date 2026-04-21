from datetime import datetime, timezone

from flask import Blueprint, jsonify, request

from app.services.reporting import build_report, latest_prices, pipeline_summary, price_movements

api_bp = Blueprint("api", __name__)


@api_bp.route("/prices")
def prices():
    product_type = request.args.get("product_type")
    limit = int(request.args.get("limit", 200))
    records = latest_prices(product_type=product_type, limit=limit)
    return jsonify({
        "as_of": datetime.now(timezone.utc).isoformat(),
        "count": len(records),
        "records": records,
    })


@api_bp.route("/report")
def report():
    summary = pipeline_summary()
    batch_id = summary["latest_run"].get("batch_id")
    if not batch_id:
        return jsonify({"error": "no pipeline runs found"}), 404
    data = build_report(batch_id)
    return jsonify(data)


@api_bp.route("/health")
def health():
    return jsonify({"status": "ok", "service": "EnergyPulse Flask API"})
