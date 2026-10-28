"""Single-user session authentication."""

import hmac
import logging
from functools import wraps

from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash

logger = logging.getLogger(__name__)

bp = Blueprint("auth", __name__)


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


def _credentials_valid(username, password):
    configured_username = current_app.config.get("APP_USERNAME", "")
    stored_hash = current_app.config.get("APP_PASSWORD_HASH", "")
    plain_password = current_app.config.get("APP_PASSWORD", "")

    if not configured_username:
        return False
    if not stored_hash and not plain_password:
        return False

    try:
        username_ok = hmac.compare_digest(
            username.encode("utf-8"), configured_username.encode("utf-8")
        )
    except Exception:
        username_ok = username == configured_username
    if not username_ok:
        return False

    if stored_hash:
        try:
            if check_password_hash(stored_hash, password):
                return True
        except (ValueError, TypeError):
            pass

    if plain_password:
        try:
            if hmac.compare_digest(password.encode("utf-8"), plain_password.encode("utf-8")):
                return True
        except Exception:
            if password == plain_password:
                return True

    return False


@bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("authenticated"):
        return redirect(url_for("dashboard.index"))

    username = ""
    error = None

    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""

        if not current_app.config.get("APP_USERNAME") or (
            not current_app.config.get("APP_PASSWORD_HASH")
            and not current_app.config.get("APP_PASSWORD")
        ):
            logger.error(
                "Login attempted but APP_USERNAME or APP_PASSWORD/APP_PASSWORD_HASH is not configured."
            )
            error = "Login is not configured on the server."
        elif _credentials_valid(username, password):
            session.clear()
            session.permanent = True
            session["authenticated"] = True
            session["user"] = current_app.config["APP_USERNAME"]
            logger.info("Successful login.")
            return redirect(url_for("dashboard.index"))
        else:
            logger.warning("Failed login attempt.")
            error = "Invalid username or password."

    return render_template("login.html", error=error, username=username)


@bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("You have been signed out.", "success")
    return redirect(url_for("auth.login"))
