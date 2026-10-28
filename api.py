"""REST API for mobile clients."""

import math

from bson.errors import InvalidId
from bson.objectid import ObjectId
from flask import Blueprint, current_app, jsonify, request, session
from pymongo import ASCENDING, DESCENDING
from werkzeug.security import check_password_hash

from database import get_collection
from utils.categories import CATEGORIES, TYPE_LABELS
from utils.dates import (
    format_date,
    local_today,
    month_bounds,
    month_label,
    utcnow_naive,
)
from utils.filters import parse_filters
from utils.money import as_decimal128, to_decimal
from utils.stats import chart_payload, documents_in_month, summarize
from utils.validation import validate_transaction_form

bp = Blueprint("api", __name__, url_prefix="/api")


def api_login_required(view):
    from functools import wraps

    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if request.method == "OPTIONS":
            return view(*args, **kwargs)
        if not session.get("authenticated"):
            return jsonify({"error": "Unauthorized"}), 401
        return view(*args, **kwargs)

    return wrapped_view


def _object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def _serialize_transaction(doc):
    amount = to_decimal(doc.get("amount"))
    return {
        "_id": str(doc["_id"]),
        "type": doc.get("type"),
        "type_label": TYPE_LABELS.get(doc.get("type"), doc.get("type")),
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "amount": f"{amount:.2f}",
        "amount_value": str(amount),
        "amount_formatted": f"{amount:,.2f}",
        "date": format_date(doc.get("date")),
        "category": doc.get("category", ""),
        "payment_method": doc.get("payment_method", ""),
        "notes": doc.get("notes", ""),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
        "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
    }


@bp.route("/auth/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or request.form.get("username") or "").strip()
    password = data.get("password") or request.form.get("password") or ""

    configured_username = current_app.config.get("APP_USERNAME", "")
    stored_hash = current_app.config.get("APP_PASSWORD_HASH", "")
    plain_password = current_app.config.get("APP_PASSWORD", "")

    if not configured_username or (not stored_hash and not plain_password):
        return jsonify({"error": "Login is not configured on the server."}), 500

    import hmac

    username_ok = hmac.compare_digest(username.encode("utf-8"), configured_username.encode("utf-8"))
    if not username_ok:
        return jsonify({"error": "Invalid username or password."}), 401

    password_ok = False
    if stored_hash:
        try:
            password_ok = check_password_hash(stored_hash, password)
        except (ValueError, TypeError):
            password_ok = False
    if not password_ok and plain_password:
        try:
            password_ok = hmac.compare_digest(password.encode("utf-8"), plain_password.encode("utf-8"))
        except Exception:
            password_ok = False

    if password_ok:
        session.clear()
        session.permanent = True
        session["authenticated"] = True
        session["user"] = configured_username
        return jsonify({"success": True, "user": configured_username}), 200

    return jsonify({"error": "Invalid username or password."}), 401


@bp.route("/auth/logout", methods=["POST"])
@api_login_required
def api_logout():
    session.clear()
    return jsonify({"success": True}), 200


@bp.route("/auth/status", methods=["GET"])
def api_status():
    if session.get("authenticated"):
        return jsonify({"authenticated": True, "user": session.get("user")}), 200
    return jsonify({"authenticated": False}), 200


@bp.route("/dashboard", methods=["GET"])
@api_login_required
def api_dashboard():
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

    return jsonify(
        {
            "all_time": {
                "credits": f"{overall['credits']:.2f}",
                "debits": f"{overall['debits']:.2f}",
                "net": f"{overall['net']:.2f}",
            },
            "current_month": {
                "credits": f"{monthly['credits']:.2f}",
                "debits": f"{monthly['debits']:.2f}",
                "net": f"{monthly['net']:.2f}",
            },
            "monthly_trend": [
                {"month": month, "credits": credits, "debits": debits}
                for month, credits, debits in zip(
                    charts["trend"]["labels"],
                    charts["trend"]["credits"],
                    charts["trend"]["debits"],
                )
            ],
            "category_spending": [
                {"category": category, "total": total}
                for category, total in zip(
                    charts["categories"]["labels"],
                    charts["categories"]["totals"],
                )
            ],
            "recent_transactions": [_serialize_transaction(doc) for doc in recent],
            "month_name": month_label(today.year, today.month),
        }
    ), 200


@bp.route("/transactions", methods=["GET"])
@api_login_required
def api_transactions():
    query, filters, errors = parse_filters(request.args, include_sort=True)
    collection = get_collection()
    try:
        page = int(request.args.get("page", "1"))
    except (TypeError, ValueError):
        page = 1
    page = max(page, 1)

    total = collection.count_documents(query)
    pages = max(1, math.ceil(total / 15))
    page = min(page, pages)

    if filters["sort"] == "date_asc":
        sort_order = [("date", ASCENDING), ("created_at", ASCENDING)]
    else:
        sort_order = [("date", DESCENDING), ("created_at", DESCENDING)]

    documents = list(
        collection.find(query)
        .sort(sort_order)
        .skip((page - 1) * 15)
        .limit(15)
    )

    return jsonify(
        {
            "transactions": [_serialize_transaction(doc) for doc in documents],
            "pagination": {
                "page": page,
                "pages": pages,
                "total": total,
                "per_page": 15,
            },
            "filters": filters,
            "errors": errors,
        }
    ), 200


@bp.route("/transactions", methods=["POST"])
@api_login_required
def api_create_transaction():
    _data, errors, parsed = validate_transaction_form(request.json or request.form)
    if errors:
        return jsonify({"errors": errors}), 400

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
    result = get_collection().insert_one(document)
    document["_id"] = result.inserted_id
    return jsonify({"success": True, "transaction": _serialize_transaction(document)}), 201


@bp.route("/transactions/<transaction_id>", methods=["GET"])
@api_login_required
def api_get_transaction(transaction_id):
    oid = _object_id(transaction_id)
    if oid is None:
        return jsonify({"error": "Not found"}), 404
    document = get_collection().find_one({"_id": oid})
    if document is None:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"transaction": _serialize_transaction(document)}), 200


@bp.route("/transactions/<transaction_id>", methods=["PUT", "PATCH"])
@api_login_required
def api_update_transaction(transaction_id):
    oid = _object_id(transaction_id)
    if oid is None:
        return jsonify({"error": "Not found"}), 404

    _data, errors, parsed = validate_transaction_form(request.json or request.form)
    if errors:
        return jsonify({"errors": errors}), 400

    collection = get_collection()
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
        return jsonify({"error": "Not found"}), 404

    document = collection.find_one({"_id": oid})
    return jsonify({"success": True, "transaction": _serialize_transaction(document)}), 200


@bp.route("/transactions/<transaction_id>", methods=["DELETE"])
@api_login_required
def api_delete_transaction(transaction_id):
    oid = _object_id(transaction_id)
    if oid is None:
        return jsonify({"error": "Not found"}), 404
    result = get_collection().delete_one({"_id": oid})
    if result.deleted_count == 0:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"success": True}), 200


@bp.route("/categories", methods=["GET"])
@api_login_required
def api_categories():
    return jsonify({"categories": CATEGORIES, "types": TYPE_LABELS}), 200


@bp.route("/stats", methods=["GET"])
@api_login_required
def api_stats():
    today = local_today(current_app)
    start, end = month_bounds(today)
    documents = list(get_collection().find({}))
    overall = summarize(documents)
    monthly = summarize(documents_in_month(documents, start, end))
    return jsonify(
        {
            "all_time_credits": f"{overall['credits']:.2f}",
            "all_time_debits": f"{overall['debits']:.2f}",
            "all_time_net": f"{overall['net']:.2f}",
            "current_month_credits": f"{monthly['credits']:.2f}",
            "current_month_debits": f"{monthly['debits']:.2f}",
            "current_month_net": f"{monthly['net']:.2f}",
        }
    ), 200
