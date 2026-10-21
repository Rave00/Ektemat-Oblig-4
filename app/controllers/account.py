"""Customer accounts: log in and log out (plan 0). Registration, orders and questions follow in plans 3-5."""
from flask import Blueprint, flash, redirect, render_template, request, url_for
from werkzeug.security import check_password_hash

from . import repos
from .security import log_in, log_out, safe_next

bp = Blueprint("account", __name__, url_prefix="/account")


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        user = repos().users.get_by_email(email)
        if user and check_password_hash(user.password_hash, password):
            log_in(user)
            flash(f"Welcome, {user.name}.", "success")
            return redirect(safe_next(request.form.get("next")))
        # The same message whether the e-mail or the password was wrong (lab backlog US-47).
        flash("Wrong e-mail or password.", "error")
        return render_template("account/login.html", email=email, next=request.form.get("next", "")), 401
    return render_template("account/login.html", email="", next=request.args.get("next", ""))


@bp.route("/logout", methods=["POST"])
def logout():
    log_out()
    flash("You are logged out.", "success")
    return redirect(url_for("shop.index"))
