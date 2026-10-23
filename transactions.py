"""Transaction list, detail, create, edit and delete routes."""

import math

from bson.errors import InvalidId
from bson.objectid import ObjectId
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from pymongo import ASCENDING, DESCENDING

from auth import login_required
from database import get_collection
from utils.categories import CATEGORIES
from utils.dates import format_date, today_string, utcnow_naive
from utils.filters import parse_filters
from utils.money import as_decimal128, format_money_input
from utils.validation import validate_transaction_form

bp = Blueprint("transactions", __name__, url_prefix="/transactions")

PER_PAGE = 15


def _object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        abort(404)


def _blank_form_data():
    return {
        "type": "debit",
        "title": "",
        "description": "",
        "amount": "",
        "date": today_string(current_app),
        "category": "",
        "payment_method": "",
        "notes": "",
    }


def _form_data_from_document(doc):
    return {
        "type": doc.get("type", ""),
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "amount": format_money_input(doc.get("amount", 0)),
        "date": format_date(doc.get("date")),
        "category": doc.get("category", ""),
        "payment_method": doc.get("payment_method", ""),
        "notes": doc.get("notes", ""),
    }


def _pagination(page, pages, total):
    def page_url(number):
        args = request.args.to_dict(flat=True)
        args["page"] = number
        return url_for("transactions.index", **args)

    return {
        "page": page,
        "pages": pages,
        "total": total,
        "per_page": PER_PAGE,
        "has_prev": page > 1,
        "has_next": page < pages,
        "prev_url": page_url(page - 1) if page > 1 else None,
        "next_url": page_url(page + 1) if page < pages else None,
        "page_items": [
            {"number": number, "url": page_url(number)}
            for number in range(max(1, page - 2), min(pages, page + 2) + 1)
        ],
    }


@bp.route("")
@login_required
def index():
    query, filters, errors = parse_filters(request.args, include_sort=True)
    collection = get_collection()

    try:
        page = int(request.args.get("page", "1"))
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)

    total = collection.count_documents(query)
    pages = max(1, math.ceil(total / PER_PAGE))
    page = min(page, pages)

    if filters["sort"] == "date_asc":
        sort_order = [("date", ASCENDING), ("created_at", ASCENDING)]
    else:
        sort_order = [("date", DESCENDING), ("created_at", DESCENDING)]

    documents = list(
        collection.find(query)
        .sort(sort_order)
        .skip((page - 1) * PER_PAGE)
        .limit(PER_PAGE)
    )

    return render_template(
        "transactions.html",
        page_title="Transactions",
        transactions=documents,
        filters=filters,
        errors=errors,
        pagination=_pagination(page, pages, total),
        start_index=(page - 1) * PER_PAGE,
        categories=CATEGORIES,
        has_filters=any(
            filters[key] not in ("", "all", "date_desc")
            for key in ("q", "type", "category", "start_date", "end_date", "sort")
        ),
    )


@bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "GET":
        return render_template(
            "transaction_form.html",
            page_title="Add Transaction",
            mode="create",
            data=_blank_form_data(),
            errors={},
            categories=CATEGORIES,
            transaction=None,
        )

    data, errors, parsed = validate_transaction_form(request.form)
    if errors:
        return (
            render_template(
                "transaction_form.html",
                page_title="Add Transaction",
                mode="create",
                data=data,
                errors=errors,
                categories=CATEGORIES,
                transaction=None,
            ),
            400,
        )

    now = utcnow_naive()
    document = {
        "type": parsed["type"],
        "title": parsed["title"],
        "description": parsed["description"],
        "amount": as_decimal128(parsed["amount"]),
        "date": parsed["date"],
        "category": parsed["category"],
        "payment_method": parsed["payment_method"],
        "notes": parsed["notes"],
        "created_at": now,
        "updated_at": now,
    }
    get_collection().insert_one(document)
    flash("Transaction saved.", "success")
    return redirect(url_for("transactions.index"))


@bp.route("/<transaction_id>")
@login_required
def detail(transaction_id):
    oid = _object_id(transaction_id)
    document = get_collection().find_one({"_id": oid})
    if document is None:
        abort(404)
    return render_template(
        "transaction_detail.html",
        page_title="Transaction Details",
        transaction=document,
    )


@bp.route("/<transaction_id>/edit", methods=["GET", "POST"])
@login_required
def edit(transaction_id):
    oid = _object_id(transaction_id)
    collection = get_collection()
    document = collection.find_one({"_id": oid})
    if document is None:
        abort(404)

    if request.method == "GET":
        return render_template(
            "transaction_form.html",
            page_title="Edit Transaction",
            mode="edit",
            data=_form_data_from_document(document),
            errors={},
            categories=CATEGORIES,
            transaction=document,
        )

    data, errors, parsed = validate_transaction_form(request.form)
    if errors:
        return (
            render_template(
                "transaction_form.html",
                page_title="Edit Transaction",
                mode="edit",
                data=data,
                errors=errors,
                categories=CATEGORIES,
                transaction=document,
            ),
            400,
        )

    result = collection.update_one(
        {"_id": oid},
        {
            "$set": {
                "type": parsed["type"],
                "title": parsed["title"],
                "description": parsed["description"],
                "amount": as_decimal128(parsed["amount"]),
                "date": parsed["date"],
                "category": parsed["category"],
                "payment_method": parsed["payment_method"],
                "notes": parsed["notes"],
                "updated_at": utcnow_naive(),
            }
        },
    )
    if result.matched_count == 0:
        abort(404)

    flash("Transaction updated.", "success")
    return redirect(url_for("transactions.index"))


@bp.route("/<transaction_id>/delete", methods=["POST"])
@login_required
def delete(transaction_id):
    oid = _object_id(transaction_id)
    result = get_collection().delete_one({"_id": oid})
    if result.deleted_count == 0:
        flash("That transaction no longer exists.", "error")
    else:
        flash("Transaction deleted.", "success")
    return redirect(url_for("transactions.index"))
