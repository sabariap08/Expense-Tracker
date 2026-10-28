"""Expense Tracker application factory."""

import logging

from flask import (
    Flask,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_cors import CORS
from flask_wtf.csrf import CSRFError, CSRFProtect
from pymongo.errors import PyMongoError

from config import Config
from database import DatabaseUnavailable, init_database
from utils.categories import TYPE_LABELS
from utils.dates import format_date
from utils.money import format_money

csrf = CSRFProtect()


def create_app(config_object=None, database=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if config_object is not None:
        if isinstance(config_object, dict):
            app.config.update(config_object)
        else:
            app.config.from_object(config_object)

    secret_key = app.config.get("SECRET_KEY") or ""
    if not secret_key:
        raise RuntimeError(
            "SECRET_KEY is not configured. Copy .env.example to .env and set "
            "a long random value before starting the application."
        )
    if secret_key == "replace_with_a_long_random_secret" or len(secret_key) < 32:
        raise RuntimeError(
            "SECRET_KEY is too short or still set to the example placeholder. "
            "Generate at least 32 random characters, for example with: "
            'python -c "import secrets; print(secrets.token_hex(32))"'
        )

    _configure_logging(app)

    if database is None:
        init_database(app)
    else:
        app.extensions["database"] = database

    csrf.init_app(app)
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    from api import bp as api_bp
    from auth import bp as auth_bp
    from dashboard import bp as dashboard_bp
    from reports import bp as reports_bp
    from transactions import bp as transactions_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(transactions_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(api_bp)

    from auth import login_required

    @app.route("/settings")
    @login_required
    def settings():
        return render_template("settings.html", page_title="Settings")

    app.jinja_env.filters["money"] = format_money
    app.jinja_env.filters["datefmt"] = format_date
    app.jinja_env.filters["type_label"] = lambda value: TYPE_LABELS.get(
        value, str(value).title()
    )

    @app.after_request
    def set_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "same-origin")
        if request.endpoint and request.endpoint.startswith("api."):
            response.headers["Cache-Control"] = "no-store"
            return response
        if request.endpoint != "static" and response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store"
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; "
            "script-src 'self' https://cdn.jsdelivr.net; "
            "style-src 'self'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'",
        )
        return response

    @app.errorhandler(DatabaseUnavailable)
    def database_unavailable(error):
        current_app.logger.error("Database unavailable: %s", error)
        return (
            render_template(
                "error.html",
                page_title="Database unavailable",
                title="Database unavailable",
                message=str(error),
            ),
            503,
        )

    @app.errorhandler(PyMongoError)
    def mongo_error(error):
        current_app.logger.error(
            "MongoDB operation failed (%s).", type(error).__name__
        )
        return (
            render_template(
                "error.html",
                page_title="Database error",
                title="Database error",
                message=(
                    "The database could not complete this request. Please try "
                    "again in a moment."
                ),
            ),
            503,
        )

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        current_app.logger.warning("CSRF validation failed: %s", error.description)
        flash("Your form session expired. Please try again.", "error")
        if session.get("authenticated"):
            return redirect(url_for("dashboard.index"))
        return redirect(url_for("auth.login"))

    @app.errorhandler(404)
    def not_found(error):
        return (
            render_template(
                "error.html",
                page_title="Page not found",
                title="Page not found",
                message="The page you requested does not exist.",
            ),
            404,
        )

    @app.errorhandler(405)
    def method_not_allowed(error):
        return (
            render_template(
                "error.html",
                page_title="Method not allowed",
                title="Method not allowed",
                message="That request is not allowed for this page.",
            ),
            405,
        )

    @app.errorhandler(500)
    def internal_error(error):
        original = getattr(error, "original_exception", None)
        current_app.logger.error(
            "Internal server error (%s).",
            type(original).__name__ if original else "unknown",
            exc_info=original if original is not None else False,
        )
        return (
            render_template(
                "error.html",
                page_title="Something went wrong",
                title="Something went wrong",
                message="The application could not complete your request.",
            ),
            500,
        )

    return app


def _configure_logging(app):
    if app.config.get("TESTING"):
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


# Keep logging predictable when the module is imported by a WSGI server.
logging.getLogger("pymongo").setLevel(logging.WARNING)
logging.getLogger("werkzeug").setLevel(logging.INFO)
