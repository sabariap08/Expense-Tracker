from datetime import datetime, timedelta
from io import BytesIO

from pypdf import PdfReader


def report_form(**overrides):
    data = {
        "start_date": "",
        "end_date": "",
        "type": "all",
        "category": "all",
        "q": "",
    }
    data.update(overrides)
    return data


def pdf_text(response):
    reader = PdfReader(BytesIO(response.data))
    return "\n".join(page.extract_text() or "" for page in reader.pages), reader


def test_reports_page_shows_matching_summary(auth_client, add_transaction):
    add_transaction(
        title="Salary",
        transaction_type="credit",
        amount="1000.00",
        category="Salary",
        date=datetime(2026, 1, 5),
    )
    add_transaction(
        title="Groceries",
        transaction_type="debit",
        amount="250.00",
        category="Food",
        date=datetime(2026, 1, 6),
    )

    response = auth_client.get("/reports")
    assert response.status_code == 200
    assert b"2 transactions match" in response.data
    assert b"1,000.00" in response.data
    assert b"250.00" in response.data
    assert b"750.00" in response.data


def test_report_rejects_invalid_date_range(auth_client):
    response = auth_client.post(
        "/reports/pdf",
        data=report_form(start_date="2026-02-01", end_date="2026-01-01"),
    )
    assert response.status_code == 400
    assert b"Start date cannot be later than the end date" in response.data
    assert response.mimetype == "text/html"


def test_report_with_no_matches_shows_message(auth_client, add_transaction):
    add_transaction(title="Salary", transaction_type="credit", amount="1000.00")
    response = auth_client.post(
        "/reports/pdf",
        data=report_form(type="debit"),
        follow_redirects=True,
    )
    assert b"No transactions match the selected filters" in response.data
    assert response.mimetype == "text/html"


def test_pdf_download_respects_type_filter_and_totals(auth_client, add_transaction):
    add_transaction(
        title="Salary payment",
        transaction_type="credit",
        amount="1000.00",
        category="Salary",
        date=datetime(2026, 1, 5),
    )
    add_transaction(
        title="Grocery purchase",
        transaction_type="debit",
        amount="250.50",
        category="Food",
        date=datetime(2026, 1, 6),
    )
    add_transaction(
        title="Transport pass",
        transaction_type="debit",
        amount="50.00",
        category="Transport",
        date=datetime(2026, 1, 7),
    )

    response = auth_client.post("/reports/pdf", data=report_form(type="debit"))
    assert response.status_code == 200
    assert response.mimetype == "application/pdf"
    disposition = response.headers["Content-Disposition"]
    assert "attachment" in disposition
    assert "expense_tracker_report_" in disposition
    assert disposition.endswith(".pdf")
    assert response.data.startswith(b"%PDF")

    text, reader = pdf_text(response)
    assert len(reader.pages) == 1
    assert "Expense tracker" in text
    assert "S.No." in text
    assert "Type (Credit/Debit)" in text
    assert "Grocery purchase" in text
    assert "Transport pass" in text
    assert "Salary payment" not in text
    assert "Total credits: 0.00" in text
    assert "Total debits: 300.50" in text
    assert "Net balance: -300.50" in text


def test_pdf_respects_category_date_and_keyword_filters(
    auth_client, add_transaction
):
    add_transaction(
        title="Lunch",
        transaction_type="debit",
        amount="20.00",
        category="Food",
        description="Office lunch",
        date=datetime(2026, 1, 10),
    )
    add_transaction(
        title="Dinner",
        transaction_type="debit",
        amount="40.00",
        category="Food",
        description="Family dinner",
        date=datetime(2026, 1, 20),
    )
    add_transaction(
        title="Bus",
        transaction_type="debit",
        amount="5.00",
        category="Transport",
        description="Office commute",
        date=datetime(2026, 1, 10),
    )

    response = auth_client.post(
        "/reports/pdf",
        data=report_form(
            start_date="2026-01-01",
            end_date="2026-01-15",
            category="Food",
            q="Office",
        ),
    )
    assert response.status_code == 200
    text, _ = pdf_text(response)
    assert "Lunch" in text
    assert "Dinner" not in text
    assert "Bus" not in text
    assert "Transactions: 1" in text


def test_pdf_repeats_header_on_each_page(auth_client, add_transaction):
    for day in range(1, 121):
        add_transaction(
            title=f"Transaction {day:03d}",
            transaction_type="debit",
            amount="10.00",
            category="Other",
            description="A longer description used to exercise table wrapping and pagination.",
            date=datetime(2026, 1, 1) + timedelta(days=day - 1),
        )

    response = auth_client.post("/reports/pdf", data=report_form())
    assert response.status_code == 200
    reader = PdfReader(BytesIO(response.data))
    assert len(reader.pages) > 1

    for page in reader.pages:
        page_text = page.extract_text() or ""
        assert "S.No." in page_text
        assert "Description" in page_text


def test_pdf_contains_all_matching_not_only_first_page(auth_client, add_transaction):
    for index in range(1, 41):
        add_transaction(
            title=f"Bulk item {index:02d}",
            transaction_type="debit",
            amount="1.00",
            category="Other",
            date=datetime(2026, 1, 1),
        )

    response = auth_client.post("/reports/pdf", data=report_form())
    assert response.status_code == 200
    text, _ = pdf_text(response)
    assert "Bulk item 01" in text
    assert "Bulk item 40" in text
    assert "Transactions: 40" in text
