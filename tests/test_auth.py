import re

from app import create_app
from database import Database
from tests.conftest import TEST_PASSWORD, TEST_USERNAME, TestConfig

PROTECTED_PATHS = [
    "/",
    "/transactions",
    "/transactions/new",
    "/reports",
]


def test_login_page_loads(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert b"Sign in" in response.data
    assert b"Register" not in response.data


def test_protected_routes_redirect_to_login(client):
    for path in PROTECTED_PATHS:
        response = client.get(path)
        assert response.status_code == 302
        assert "/login" in response.headers["Location"]


def test_incorrect_credentials_are_rejected(client):
    response = client.post(
        "/login", data={"username": TEST_USERNAME, "password": "wrong-password"}
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data
    with client.session_transaction() as session:
        assert not session.get("authenticated")


def test_incorrect_username_is_rejected(client):
    response = client.post(
        "/login", data={"username": "someone-else", "password": TEST_PASSWORD}
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_correct_credentials_allow_login(client):
    response = client.post(
        "/login", data={"username": TEST_USERNAME, "password": TEST_PASSWORD}
    )
    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")
    with client.session_transaction() as session:
        assert session.get("authenticated") is True
        assert session.get("user") == TEST_USERNAME

    dashboard = client.get("/")
    assert dashboard.status_code == 200
    assert b"Dashboard" in dashboard.data


def test_logout_clears_session(auth_client):
    with auth_client.session_transaction() as session:
        assert session.get("authenticated") is True

    response = auth_client.post("/logout")
    assert response.status_code == 302
    with auth_client.session_transaction() as session:
        assert not session.get("authenticated")

    protected = auth_client.get("/")
    assert protected.status_code == 302
    assert "/login" in protected.headers["Location"]


def test_csrf_protection_blocks_login_without_token():
    database = Database("", "expense_tracker_test")

    class CsrfConfig(TestConfig):
        WTF_CSRF_ENABLED = True

    application = create_app(CsrfConfig, database=database)
    client = application.test_client()

    response = client.post(
        "/login",
        data={"username": TEST_USERNAME, "password": TEST_PASSWORD},
    )
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
    with client.session_transaction() as session:
        assert not session.get("authenticated")

    page = client.get("/login")
    match = re.search(
        rb'name="csrf_token" value="([^"]+)"',
        page.data,
    )
    assert match is not None
    token = match.group(1).decode()

    response = client.post(
        "/login",
        data={
            "username": TEST_USERNAME,
            "password": TEST_PASSWORD,
            "csrf_token": token,
        },
    )
    assert response.status_code == 302
    with client.session_transaction() as session:
        assert session.get("authenticated") is True
