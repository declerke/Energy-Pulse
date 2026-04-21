from flask import Blueprint, render_template

from app.services.reporting import latest_prices, pipeline_summary, price_movements

dashboard_bp = Blueprint("dashboard", __name__)


@dashboard_bp.route("/")
def index():
    prices = latest_prices(limit=50)
    movements = price_movements(top_n=5)
    summary = pipeline_summary()
    return render_template(
        "dashboard.html",
        prices=prices,
        top_increase=movements["top_increase"],
        top_decrease=movements["top_decrease"],
        summary=summary,
    )
