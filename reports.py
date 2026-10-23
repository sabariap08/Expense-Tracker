"""Filtered PDF report generation."""

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from pymongo import ASCENDING

from auth import login_required
from database import get_collection
from utils.categories import CATEGORIES
from utils.dates import local_today
from utils.filters import parse_filters
from utils.pdf import build_report_pdf
from utils.stats import summarize

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _empty_filters():
    return {
        "q": "",
        "type": "all",
        "category": "all",
        "start_date": "",
        "end_date": "",
    }


def _query_args(filters):
    return {
        "q": filters.get("q", ""),
        "type": filters.get("type", "all"),
        "category": filters.get("category", "all"),
        "start_date": filters.get("start_date", ""),
        "end_date": filters.get("end_date", ""),
    }


def _matching_documents(query):
    return list(
        get_collection()
        .find(query)
        .sort([("date", ASCENDING), ("created_at", ASCENDING)])
    )


@bp.route("")
@login_required
def index():
    query, filters, errors = parse_filters(request.args)
    summary = None

    if not errors:
        documents = _matching_documents(query)
        summary = summarize(documents)

    return render_template(
        "reports.html",
        page_title="Reports",
        filters=filters,
        errors=errors,
        summary=summary,
        categories=CATEGORIES,
    )


@bp.route("/pdf", methods=["POST"])
@login_required
def download_pdf():
    query, filters, errors = parse_filters(request.form)
    if errors:
        return (
            render_template(
                "reports.html",
                page_title="Reports",
                filters=filters,
                errors=errors,
                summary=None,
                categories=CATEGORIES,
            ),
            400,
        )

    documents = _matching_documents(query)
    if not documents:
        flash("No transactions match the selected filters.", "error")
        return redirect(url_for("reports.index", **_query_args(filters)))

    generated_on = local_today(current_app).strftime("%Y-%m-%d")
    buffer = build_report_pdf(documents, filters, generated_on)
    filename = f"expense_tracker_report_{generated_on}.pdf"

    response = send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
        max_age=0,
    )
    response.headers["Cache-Control"] = "no-store"
    return response
