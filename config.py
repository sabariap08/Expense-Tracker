"""Application configuration loaded from environment variables."""

import os
from datetime import timedelta

from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def env_bool(name, default=False):
    """Read a boolean environment value."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name, default):
    """Read an integer environment value, falling back to a default."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "").strip()

    MONGODB_URI = os.environ.get("MONGODB_URI", "").strip()
    MONGODB_DATABASE = (
        os.environ.get("MONGODB_DATABASE", "expense_tracker").strip()
        or "expense_tracker"
    )

    APP_USERNAME = os.environ.get("APP_USERNAME", "").strip()
    APP_PASSWORD_HASH = os.environ.get("APP_PASSWORD_HASH", "").strip()
    APP_PASSWORD = os.environ.get("APP_PASSWORD", "").strip()

    APP_TIMEZONE = os.environ.get("APP_TIMEZONE", "UTC").strip() or "UTC"

    FLASK_DEBUG = env_bool("FLASK_DEBUG", False)

    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", not FLASK_DEBUG)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    PERMANENT_SESSION_LIFETIME = timedelta(
        hours=env_int("SESSION_LIFETIME_HOURS", 12)
    )

    WTF_CSRF_TIME_LIMIT = env_int("SESSION_LIFETIME_HOURS", 12) * 3600

    MAX_CONTENT_LENGTH = 1024 * 1024
