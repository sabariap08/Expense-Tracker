from datetime import datetime

import mongomock
import pytest
from bson.decimal128 import Decimal128
from werkzeug.security import generate_password_hash

from app import create_app
from database import Database

TEST_USERNAME = "tester"
TEST_PASSWORD = "test-password-123"


class TestConfig:
    SECRET_KEY = "test-secret-key-for-unit-tests-1234567890"
    TESTING = True
    WTF_CSRF_ENABLED = False
    SESSION_COOKIE_SECURE = False
    APP_USERNAME = TEST_USERNAME
    APP_PASSWORD_HASH = generate_password_hash(TEST_PASSWORD)
    APP_TIMEZONE = "UTC"
    MONGODB_URI = ""
    MONGODB_DATABASE = "expense_tracker_test"
    FLASK_DEBUG = False


@pytest.fixture
def app():
    database = Database("", "expense_tracker_test")
    database.collection = mongomock.MongoClient()["expense_tracker_test"][
        "transactions"
    ]
    application = create_app(TestConfig, database=database)
    yield application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_client(client):
    response = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 302
    return client


@pytest.fixture
def collection(app):
    return app.extensions["database"].collection


@pytest.fixture
def add_transaction(collection):
    def _add(
        title="Test transaction",
        transaction_type="debit",
        amount="100.00",
        date=None,
        category="Food",
        description="",
        payment_method="",
        notes="",
    ):
        document = {
            "type": transaction_type,
            "title": title,
            "description": description,
            "amount": Decimal128(amount),
            "date": date or datetime(2026, 1, 15),
            "category": category,
            "payment_method": payment_method,
            "notes": notes,
            "created_at": datetime(2026, 1, 15, 10, 0, 0),
            "updated_at": datetime(2026, 1, 15, 10, 0, 0),
        }
        result = collection.insert_one(document)
        return result.inserted_id

    return _add
