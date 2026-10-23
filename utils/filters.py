"""Shared query-string parsing for transaction lists and reports."""

import re

from utils.categories import CATEGORIES, TYPES
from utils.dates import parse_date

KEYWORD_MAX = 100
SORTS = {"date_desc", "date_asc"}


def _clean(value):
    return (value or "").strip()


def parse_filters(args, include_sort=False):
    """Build a safe MongoDB query from filter arguments.

    Unknown types and categories are rejected by returning a validation error
    instead of being passed through to the database.
    """
    filters = {
        "q": _clean(args.get("q")),
        "type": _clean(args.get("type")) or "all",
        "category": _clean(args.get("category")) or "all",
        "start_date": _clean(args.get("start_date")),
        "end_date": _clean(args.get("end_date")),
    }
    if include_sort:
        filters["sort"] = _clean(args.get("sort")) or "date_desc"

    errors = []
    query = {}

    if len(filters["q"]) > KEYWORD_MAX:
        errors.append(f"Search text must be {KEYWORD_MAX} characters or fewer.")
        filters["q"] = filters["q"][:KEYWORD_MAX]
    if filters["q"]:
        pattern = re.escape(filters["q"])
        query["$or"] = [
            {"title": {"$regex": pattern, "$options": "i"}},
            {"description": {"$regex": pattern, "$options": "i"}},
        ]

    if filters["type"] != "all":
        if filters["type"] in TYPES:
            query["type"] = filters["type"]
        else:
            errors.append("Invalid transaction type filter.")
            filters["type"] = "all"

    if filters["category"] != "all":
        if filters["category"] in CATEGORIES:
            query["category"] = filters["category"]
        else:
            errors.append("Invalid category filter.")
            filters["category"] = "all"

    if include_sort and filters["sort"] not in SORTS:
        errors.append("Invalid sort option.")
        filters["sort"] = "date_desc"

    start = end = None
    if filters["start_date"]:
        try:
            start = parse_date(filters["start_date"])
        except ValueError as exc:
            errors.append(f"Start date: {exc}")
    if filters["end_date"]:
        try:
            end = parse_date(filters["end_date"])
        except ValueError as exc:
            errors.append(f"End date: {exc}")

    if start and end and start > end:
        errors.append("Start date cannot be later than the end date.")
    else:
        date_query = {}
        if start:
            date_query["$gte"] = start
        if end:
            date_query["$lte"] = end
        if date_query:
            query["date"] = date_query

    return query, filters, errors
