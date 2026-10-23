"""Server-side validation for transaction forms."""

from utils.categories import CATEGORIES, TYPES
from utils.dates import parse_date
from utils.money import AmountError, parse_amount

TITLE_MAX = 120
DESCRIPTION_MAX = 1000
PAYMENT_METHOD_MAX = 80
NOTES_MAX = 500

FORM_FIELDS = (
    "type",
    "title",
    "description",
    "amount",
    "date",
    "category",
    "payment_method",
    "notes",
)


def validate_transaction_form(form):
    """Validate a transaction form.

    Returns (data, errors, parsed). ``data`` always contains trimmed strings
    suitable for re-rendering the form. ``parsed`` contains the Decimal amount
    and datetime date when those fields are valid.
    """
    data = {}
    for field in FORM_FIELDS:
        data[field] = (form.get(field) or "").strip()

    errors = {}
    parsed = {}

    transaction_type = data["type"].lower()
    if transaction_type not in TYPES:
        errors["type"] = "Choose Credit or Debit."
    else:
        parsed["type"] = transaction_type

    title = data["title"]
    if not title:
        errors["title"] = "Title is required."
    elif len(title) > TITLE_MAX:
        errors["title"] = f"Title must be {TITLE_MAX} characters or fewer."
    else:
        parsed["title"] = title

    description = data["description"]
    if len(description) > DESCRIPTION_MAX:
        errors["description"] = (
            f"Description must be {DESCRIPTION_MAX} characters or fewer."
        )
    else:
        parsed["description"] = description

    try:
        parsed["amount"] = parse_amount(data["amount"])
    except AmountError as exc:
        errors["amount"] = str(exc)

    try:
        parsed["date"] = parse_date(data["date"])
    except ValueError as exc:
        errors["date"] = str(exc)

    category = data["category"]
    if category not in CATEGORIES:
        errors["category"] = "Choose a category."
    else:
        parsed["category"] = category

    payment_method = data["payment_method"]
    if len(payment_method) > PAYMENT_METHOD_MAX:
        errors["payment_method"] = (
            f"Payment method must be {PAYMENT_METHOD_MAX} characters or fewer."
        )
    else:
        parsed["payment_method"] = payment_method

    notes = data["notes"]
    if len(notes) > NOTES_MAX:
        errors["notes"] = f"Notes must be {NOTES_MAX} characters or fewer."
    else:
        parsed["notes"] = notes

    return data, errors, parsed
