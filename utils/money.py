"""Exact monetary parsing, storage and formatting helpers."""

import re
from decimal import Decimal, InvalidOperation

from bson.decimal128 import Decimal128

CENT = Decimal("0.01")
ZERO = Decimal("0.00")
MAX_AMOUNT = Decimal(1000000000000)  # one trillion
_AMOUNT_PATTERN = re.compile(r"^\d+(?:\.\d{1,2})?$")


class AmountError(ValueError):
    """Raised when an amount is not a valid positive monetary value."""


def to_decimal(value):
    """Convert a stored or user supplied value to a two-place Decimal."""
    if isinstance(value, Decimal128):
        value = value.to_decimal()
    if isinstance(value, Decimal):
        return value.quantize(CENT)
    if isinstance(value, bool):
        raise AmountError("Invalid amount.")
    try:
        return Decimal(str(value)).quantize(CENT)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise AmountError("Invalid amount.") from exc


def parse_amount(raw):
    """Parse a positive amount with at most two decimal places."""
    if raw is None:
        raise AmountError("Amount is required.")
    text = str(raw).strip()
    if not text:
        raise AmountError("Amount is required.")
    if not _AMOUNT_PATTERN.match(text):
        raise AmountError(
            "Enter a positive amount with at most two decimal places."
        )
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise AmountError("Enter a valid numeric amount.") from exc
    if not value.is_finite() or value <= ZERO:
        raise AmountError("Amount must be greater than zero.")
    if value > MAX_AMOUNT:
        raise AmountError("Amount is too large.")
    return value.quantize(CENT)


def as_decimal128(value):
    return Decimal128(to_decimal(value))


def format_money(value):
    return f"{to_decimal(value):,.2f}"


def format_money_input(value):
    return f"{to_decimal(value):.2f}"


def money_float(value):
    return float(to_decimal(value))
