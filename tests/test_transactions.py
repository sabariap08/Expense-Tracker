import html
import json
import re
from datetime import UTC, datetime

import pytest
from bson.decimal128 import Decimal128
from bson.objectid import ObjectId

from app import create_app
from database import Database
from tests.conftest import TestConfig


def valid_form(**overrides):
    data = {
        "type": "debit",
        "title": "Groceries",
        "description": "Weekly grocery purchase",
        "amount": "1250.50",
        "date": "2026-02-10",
        "category": "Food",
        "payment_method": "UPI",
        "notes": "Reference 123",
    }
    data.update(overrides)
    return data


def test_add_form_defaults_to_today(auth_client):
    expected = datetime.now(UTC).date().strftime("%Y-%m-%d")
    response = auth_client.get("/transactions/new")
    assert response.status_code == 200
    assert f'value="{expected}"'.encode() in response.data
    assert b'type="radio"' in response.data


def test_create_credit_and_debit(auth_client, collection):
    credit = auth_client.post(
        "/transactions/new",
        data=valid_form(type="credit", title="Salary", amount="5000.00"),
    )
    assert credit.status_code == 302

    debit = auth_client.post(
        "/transactions/new",
        data=valid_form(type="debit", title="Rent", amount="1200.25"),
    )
    assert debit.status_code == 302

    documents = list(collection.find().sort("date", 1))
    assert len(documents) == 2
    assert {doc["type"] for doc in documents} == {"credit", "debit"}
    assert documents[1]["title"] == "Rent"
    assert isinstance(documents[1]["amount"], Decimal128)
    assert documents[1]["amount"].to_decimal() == Decimal128("1200.25").to_decimal()
    assert documents[1]["date"] == datetime(2026, 2, 10)
    assert documents[0]["created_at"] is not None


@pytest.mark.parametrize(
    "field,value,message",
    [
        ("amount", "0", b"greater than zero"),
        ("amount", "-5", b"positive amount"),
        ("amount", "abc", b"positive amount"),
        ("amount", "12.345", b"at most two decimal places"),
        ("title", "", b"Title is required"),
        ("category", "", b"Choose a category"),
        ("type", "", b"Choose Credit or Debit"),
        ("date", "2026-13-01", b"valid date"),
        ("date", "", b"valid date"),
    ],
)
def test_invalid_transactions_are_rejected(
    auth_client, collection, field, value, message
):
    response = auth_client.post(
        "/transactions/new", data=valid_form(**{field: value})
    )
    assert response.status_code == 400
    assert message in response.data
    assert collection.count_documents({}) == 0


def test_edit_updates_only_the_selected_transaction(auth_client, collection):
    first_id = collection.insert_one(
        {
            "type": "debit",
            "title": "First",
            "description": "",
            "amount": Decimal128("10.00"),
            "date": datetime(2026, 1, 1),
            "category": "Food",
            "payment_method": "",
            "notes": "",
            "created_at": datetime(2026, 1, 1),
            "updated_at": datetime(2026, 1, 1),
        }
    ).inserted_id
    second_id = collection.insert_one(
        {
            "type": "credit",
            "title": "Second",
            "description": "",
            "amount": Decimal128("20.00"),
            "date": datetime(2026, 1, 2),
            "category": "Salary",
            "payment_method": "",
            "notes": "",
            "created_at": datetime(2026, 1, 2),
            "updated_at": datetime(2026, 1, 2),
        }
    ).inserted_id

    page = auth_client.get(f"/transactions/{first_id}/edit")
    assert page.status_code == 200
    assert b"First" in page.data

    response = auth_client.post(
        f"/transactions/{first_id}/edit",
        data=valid_form(title="First updated", amount="99.99"),
    )
    assert response.status_code == 302

    first = collection.find_one({"_id": first_id})
    second = collection.find_one({"_id": second_id})
    assert first["title"] == "First updated"
    assert first["amount"].to_decimal() == Decimal128("99.99").to_decimal()
    assert second["title"] == "Second"
    assert second["amount"].to_decimal() == Decimal128("20.00").to_decimal()


def test_transaction_detail_and_invalid_ids(auth_client, add_transaction):
    transaction_id = add_transaction(title="Detail test", description="Shown here")
    response = auth_client.get(f"/transactions/{transaction_id}")
    assert response.status_code == 200
    assert b"Detail test" in response.data
    assert b"Shown here" in response.data

    missing = auth_client.get(f"/transactions/{ObjectId()}")
    assert missing.status_code == 404
    invalid = auth_client.get("/transactions/not-an-object-id")
    assert invalid.status_code == 404


def test_delete_affects_only_selected_transaction(auth_client, collection, add_transaction):
    first_id = add_transaction(title="Delete me")
    second_id = add_transaction(title="Keep me")

    response = auth_client.post(f"/transactions/{first_id}/delete")
    assert response.status_code == 302
    assert collection.count_documents({}) == 1
    assert collection.find_one({"_id": second_id}) is not None

    auth_client.post(f"/transactions/{first_id}/delete")
    assert collection.count_documents({}) == 1


def test_search_filter_sort_and_pagination(auth_client, add_transaction):
    for day in range(1, 21):
        add_transaction(
            title=f"Item {day:02d}",
            date=datetime(2026, 1, day),
            category="Food",
            transaction_type="debit",
            description="Alpha note" if day == 7 else "",
        )

    first_page = auth_client.get("/transactions")
    assert b"of 20 transactions" in first_page.data
    assert b"Item 20" in first_page.data
    assert b"Item 06" in first_page.data
    assert b"Item 05" not in first_page.data

    second_page = auth_client.get("/transactions?page=2")
    assert b"Item 05" in second_page.data
    assert b"Item 01" in second_page.data
    assert b"Item 06" not in second_page.data

    filtered_page = auth_client.get(
        "/transactions?type=debit&category=Food&page=2"
    )
    assert b"of 20 transactions" in filtered_page.data
    assert b"Item 05" in filtered_page.data

    search = auth_client.get("/transactions?q=Item+07")
    assert b"of 1 transaction" in search.data
    assert b"Item 07" in search.data
    assert b"Item 08" not in search.data

    keyword = auth_client.get("/transactions?q=Alpha")
    assert b"Item 07" in keyword.data
    assert b"of 1 transaction" in keyword.data

    date_range = auth_client.get(
        "/transactions?start_date=2026-01-05&end_date=2026-01-14"
    )
    assert b"of 10 transactions" in date_range.data

    no_results = auth_client.get("/transactions?category=Transport")
    assert b"No transactions match the current filters" in no_results.data

    ascending = auth_client.get("/transactions?sort=date_asc")
    assert ascending.data.index(b"2026-01-01") < ascending.data.index(b"2026-01-15")
    assert b"2026-01-20" not in ascending.data

    descending = auth_client.get("/transactions?sort=date_desc")
    assert descending.data.index(b"2026-01-20") < descending.data.index(b"2026-01-06")
    assert b"2026-01-01" not in descending.data

    invalid_range = auth_client.get(
        "/transactions?start_date=2026-02-01&end_date=2026-01-01"
    )
    assert b"Start date cannot be later than the end date" in invalid_range.data


def test_dashboard_totals_and_monthly_statistics(auth_client, add_transaction):
    today = datetime.now(UTC)
    current_month = datetime(today.year, today.month, 10)
    if today.month == 1:
        previous_month = datetime(today.year - 1, 12, 10)
    else:
        previous_month = datetime(today.year, today.month - 1, 10)

    add_transaction(
        title="Current salary",
        transaction_type="credit",
        amount="2000.00",
        date=current_month,
        category="Salary",
    )
    add_transaction(
        title="Current food",
        transaction_type="debit",
        amount="500.00",
        date=current_month,
        category="Food",
    )
    add_transaction(
        title="Old food",
        transaction_type="debit",
        amount="100.00",
        date=previous_month,
        category="Food",
    )

    response = auth_client.get("/")
    assert response.status_code == 200
    body = response.data

    assert b"2,000.00" in body
    assert b"600.00" in body
    assert b"1,400.00" in body
    assert b"500.00" in body
    assert b"Current salary" in body
    assert b"Old food" in body


def test_dashboard_empty_state(client):
    client.post(
        "/login",
        data={"username": "tester", "password": "test-password-123"},
    )
    response = client.get("/")
    assert response.status_code == 200
    assert b"No transactions recorded yet" in response.data


def test_dashboard_chart_payload_is_valid_json(auth_client, add_transaction):
    today = datetime.now(UTC)
    add_transaction(
        title="Chart food",
        transaction_type="debit",
        amount="75.50",
        category="Food",
        date=datetime(today.year, today.month, 3),
    )

    response = auth_client.get("/")
    match = re.search(rb'data-charts="([^"]*)"', response.data)
    assert match is not None
    payload = json.loads(html.unescape(match.group(1).decode()))

    assert payload["has_data"] is True
    assert len(payload["trend"]["labels"]) == 6
    assert payload["categories"]["labels"] == ["Food"]
    assert payload["categories"]["totals"] == [75.5]


def test_decimal_totals_avoid_float_rounding(auth_client, add_transaction):
    today = datetime.now(UTC)
    add_transaction(
        title="Small one",
        transaction_type="credit",
        amount="0.10",
        date=datetime(today.year, today.month, 1),
    )
    add_transaction(
        title="Small two",
        transaction_type="credit",
        amount="0.20",
        date=datetime(today.year, today.month, 2),
    )
    response = auth_client.get("/")
    assert b"0.30" in response.data


def test_data_persists_across_app_instances(app, auth_client, add_transaction):
    add_transaction(title="Persistent transaction")
    database = app.extensions["database"]

    second_app = create_app(TestConfig, database=database)
    second_client = second_app.test_client()
    second_client.post(
        "/login",
        data={"username": "tester", "password": "test-password-123"},
    )
    response = second_client.get("/transactions")
    assert b"Persistent transaction" in response.data


def test_database_unavailable_is_handled_without_exposing_secrets(client):
    database = Database("", "expense_tracker_test")
    application = create_app(TestConfig, database=database)
    test_client = application.test_client()
    test_client.post(
        "/login",
        data={"username": "tester", "password": "test-password-123"},
    )
    response = test_client.get("/")
    assert response.status_code == 503
    assert b"Database unavailable" in response.data
    assert b"mongodb" not in response.data.lower()
