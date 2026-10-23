"""Dashboard statistics and charts."""

from flask import Blueprint, current_app, render_template, session
from pymongo import DESCENDING

from auth import login_required
from database import get_collection
from utils.dates import local_today, month_bounds, month_label
from utils.stats import (
    chart_payload,
    documents_in_month,
    summarize,
)

bp = Blueprint("dashboard", __name__)


@bp.route("/")
@login_required
def index():
    today = local_today(current_app)
    start, end = month_bounds(today)

    documents = list(
        get_collection()
        .find(
            {},
            {
                "type": 1,
                "title": 1,
                "amount": 1,
                "date": 1,
                "category": 1,
                "created_at": 1,
            },
        )
        .sort([("date", DESCENDING), ("created_at", DESCENDING)])
    )

    overall = summarize(documents)
    monthly = summarize(documents_in_month(documents, start, end))
    recent = documents[:6]
    charts = chart_payload(documents, today)

    return render_template(
        "dashboard.html",
        page_title="Dashboard",
        overall=overall,
        monthly=monthly,
        recent=recent,
        charts=charts,
        has_data=bool(documents),
        month_name=month_label(today.year, today.month),
        username=session.get("user", ""),
    )
