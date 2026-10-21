"""Log in state, access rules and CSRF protection (plan 0, decisions D6 and D7)."""
import functools
import secrets

from flask import abort, current_app, g, redirect, request, session, url_for

from . import repos


def init_app(app):
    app.before_request(_load_user)
    app.before_request(_check_csrf)
    app.context_processor(lambda: {"csrf_token": csrf_token})


# ---- log in state -----------------------------------------------------------------------------------
def log_in(user):
    session.clear()                      # a fresh session at log in prevents session fixation
    session["user_id"] = user.id


def log_out():
    session.clear()


def _load_user():
    user_id = session.get("user_id")
    g.user = repos().users.get(user_id) if user_id else None


# ---- access rules -----------------------------------------------------------------------------------
def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("account.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("account.login", next=request.path))
        if not g.user.is_admin:
            abort(403, description="The admin panel is only for Ekte Mat staff.")
        return view(*args, **kwargs)
    return wrapped


def safe_next(target):
    """Only redirect to paths on this site after log in (never to another domain)."""
    if target and target.startswith("/") and not target.startswith(("//", "/\\")):
        return target
    return url_for("shop.index")


# ---- CSRF: every POST form must send back the token from the session ---------------------------------
def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(32)
    return session["_csrf"]


def _check_csrf():
    if request.method != "POST" or not current_app.config.get("CSRF_ENABLED", True):
        return
    expected = session.get("_csrf")
    sent = request.form.get("csrf_token", "")
    if not expected or not secrets.compare_digest(sent, expected):
        abort(400, description="The form has expired or was not sent from this site. Please try again.")
