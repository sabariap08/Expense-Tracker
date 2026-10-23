"""MongoDB connection management.

The connection is attempted once during application start-up. If Atlas is
unreachable the application still boots so that the login page and a clear
error page remain available, but data routes will return HTTP 503 until the
connection is restored.
"""

import contextlib
import logging

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import PyMongoError

logger = logging.getLogger(__name__)


class DatabaseUnavailable(RuntimeError):
    """Raised when a data route is used without a working database."""


class Database:
    def __init__(self, uri, database_name, timeout_ms=6000):
        self.uri = uri
        self.database_name = database_name
        self.timeout_ms = timeout_ms
        self.client = None
        self.db = None
        self.collection = None
        self.error = None

    def connect(self):
        if not self.uri:
            self.error = (
                "MongoDB is not configured. Set MONGODB_URI in the environment."
            )
            logger.warning("MONGODB_URI is not set; database features are disabled.")
            return

        client = None
        try:
            client = MongoClient(
                self.uri,
                serverSelectionTimeoutMS=self.timeout_ms,
                connectTimeoutMS=self.timeout_ms,
                socketTimeoutMS=self.timeout_ms,
                tz_aware=False,
                appname="ExpenseTracker",
            )
            client.admin.command("ping")
            database = client[self.database_name]
            collection = database["transactions"]

            collection.create_index([("date", DESCENDING)])
            collection.create_index([("type", ASCENDING)])
            collection.create_index([("category", ASCENDING)])
            collection.create_index([("date", DESCENDING), ("type", ASCENDING)])
            collection.create_index([("date", DESCENDING), ("category", ASCENDING)])

            self.client = client
            self.db = database
            self.collection = collection
            self.error = None
            logger.info("Connected to MongoDB database '%s'.", self.database_name)
        except PyMongoError as exc:
            if client is not None:
                with contextlib.suppress(PyMongoError):  # pragma: no cover
                    client.close()
            # Only the error type is logged. Connection strings and credentials
            # are never written to logs.
            logger.error("MongoDB connection failed (%s).", type(exc).__name__)
            self.error = (
                "The database is currently unavailable. Check the MongoDB "
                "connection settings and network access, then restart the app."
            )
        except Exception as exc:  # pragma: no cover - unexpected driver errors
            if client is not None:
                with contextlib.suppress(PyMongoError):  # pragma: no cover
                    client.close()
            logger.exception(
                "Unexpected database initialisation error (%s).", type(exc).__name__
            )
            self.error = "The database could not be initialised."

    def get_collection(self):
        if self.collection is None:
            raise DatabaseUnavailable(
                self.error or "The database is currently unavailable."
            )
        return self.collection

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None
            self.db = None
            self.collection = None


def init_database(app):
    database = Database(
        app.config.get("MONGODB_URI", ""),
        app.config.get("MONGODB_DATABASE", "expense_tracker"),
    )
    database.connect()
    app.extensions["database"] = database
    return database


def get_database():
    from flask import current_app

    return current_app.extensions["database"]


def get_collection():
    return get_database().get_collection()
