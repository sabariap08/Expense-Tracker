"""Financial calculations used by the dashboard and reports."""

from utils.dates import month_key, month_label, shift_month, to_datetime
from utils.money import ZERO, money_float, to_decimal


def summarize(documents):
    credits = ZERO
    debits = ZERO
    for doc in documents:
        amount = to_decimal(doc.get("amount", 0))
        if doc.get("type") == "credit":
            credits += amount
        elif doc.get("type") == "debit":
            debits += amount
    return {
        "credits": credits,
        "debits": debits,
        "net": credits - debits,
        "count": len(documents),
    }


def documents_in_month(documents, start, end):
    selected = []
    for doc in documents:
        value = to_datetime(doc.get("date"))
        if value is not None and start <= value < end:
            selected.append(doc)
    return selected


def monthly_trend(documents, today, months=6):
    """Return credits and debits for the recent calendar months."""
    keys = []
    for offset in range(months - 1, -1, -1):
        year, month = shift_month(today.year, today.month, -offset)
        keys.append((year, month))

    totals = {key: {"credits": ZERO, "debits": ZERO} for key in keys}
    for doc in documents:
        value = to_datetime(doc.get("date"))
        if value is None:
            continue
        key = month_key(value)
        bucket = totals.get(key)
        if bucket is None:
            continue
        amount = to_decimal(doc.get("amount", 0))
        if doc.get("type") == "credit":
            bucket["credits"] += amount
        elif doc.get("type") == "debit":
            bucket["debits"] += amount

    return {
        "labels": [month_label(year, month) for year, month in keys],
        "credits": [money_float(totals[key]["credits"]) for key in keys],
        "debits": [money_float(totals[key]["debits"]) for key in keys],
    }


def category_spending(documents):
    """Return all-time debit totals grouped by category."""
    totals = {}
    for doc in documents:
        if doc.get("type") != "debit":
            continue
        category = doc.get("category") or "Other"
        totals[category] = totals.get(category, ZERO) + to_decimal(
            doc.get("amount", 0)
        )
    ordered = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return {
        "labels": [label for label, _ in ordered],
        "totals": [money_float(total) for _, total in ordered],
        "raw": dict(ordered),
    }


def chart_payload(documents, today):
    trend = monthly_trend(documents, today)
    categories = category_spending(documents)
    return {
        "trend": trend,
        "categories": categories,
        "has_data": bool(documents),
    }
