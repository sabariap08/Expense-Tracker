"""Date parsing and timezone-aware calendar helpers.

Transaction dates are calendar dates. They are stored as naive UTC midnight so
that they round-trip consistently, while "today" and "current month" are
resolved in the configured application timezone.
"""

from datetime import UTC, date, datetime, time
from zoneinfo import ZoneInfo

DATE_FORMAT = "%Y-%m-%d"
MIN_DATE = date(1900, 1, 1)
MAX_DATE = date(2100, 12, 31)


def app_timezone(app):
    name = (app.config.get("APP_TIMEZONE") or "UTC").strip()
    try:
        return ZoneInfo(name)
    except (KeyError, ValueError):
        return ZoneInfo("UTC")


def local_now(app):
    return datetime.now(app_timezone(app))


def local_today(app):
    return local_now(app).date()


def parse_date(value):
    """Parse YYYY-MM-DD into a naive midnight datetime."""
    if value is None or not str(value).strip():
        raise ValueError("A valid date is required.")
    try:
        parsed = datetime.strptime(str(value).strip(), DATE_FORMAT).date()
    except ValueError as exc:
        raise ValueError("Enter a valid date in YYYY-MM-DD format.") from exc
    if parsed < MIN_DATE or parsed > MAX_DATE:
        raise ValueError("Date must be between 1900-01-01 and 2100-12-31.")
    return datetime.combine(parsed, time.min)


def to_datetime(value):
    """Return a naive datetime for values read from MongoDB."""
    if isinstance(value, datetime):
        return value.replace(tzinfo=None) if value.tzinfo else value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    return value


def format_date(value):
    value = to_datetime(value)
    if not isinstance(value, datetime):
        return ""
    return value.strftime(DATE_FORMAT)


def today_string(app):
    return local_today(app).strftime(DATE_FORMAT)


def month_bounds(today=None):
    """Return [first day of month, first day of next month) as datetimes."""
    today = today or date.today()
    start = datetime(today.year, today.month, 1)
    if today.month == 12:
        end = datetime(today.year + 1, 1, 1)
    else:
        end = datetime(today.year, today.month + 1, 1)
    return start, end


def shift_month(year, month, delta):
    index = year * 12 + (month - 1) + delta
    new_year, new_month_index = divmod(index, 12)
    return new_year, new_month_index + 1


def month_key(value):
    value = to_datetime(value)
    return value.year, value.month


def month_label(year, month):
    return datetime(year, month, 1).strftime("%b %Y")


def utcnow_naive():
    return datetime.now(UTC).replace(tzinfo=None, microsecond=0)
