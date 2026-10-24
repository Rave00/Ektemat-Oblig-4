"""Customer accounts: log in, register, submit an order, see it, My orders and questions (plans 0 and 3-5).

The routes only translate between HTTP and the model: the rules are in app/models/domain.py and app/models/cart.py.
"""
import re
import secrets
from datetime import date, datetime, timedelta

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from ..models.cart import Cart, estimated_total_nok, order_lines_from
from ..models.domain import (EVENTS, GROUP_ROWS, MAX_DAYS_AHEAD, MAX_GUESTS, MAX_QUESTION, PAYMENT_NAMES, STATUS_NAMES,
                             Question, QuestionError, User, order_from_form, validate_question, validate_registration)
from ..models.repositories.base import EmailAlreadyUsed
from . import repos
from .security import log_in, log_out, login_required, safe_next

bp = Blueprint("account", __name__, url_prefix="/account")


# ---- log in and log out (plan 0) -------------------------------------------------------------------------
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


# ---- register (plan 3, P3-1) -----------------------------------------------------------------------------
@bp.route("/register", methods=["GET", "POST"])
def register():
    next_page = request.values.get("next", "")
    if request.method == "POST":
        form = request.form
        name, email = form.get("name", "").strip(), form.get("email", "").strip()
        errors = validate_registration(name, email, form.get("password", ""), form.get("password_again", ""))
        if not errors:
            try:                                             # the role is always "customer", never from the form
                user = repos().users.add(User(email=email, name=name, role="customer",
                                              password_hash=generate_password_hash(form["password"])))
            except EmailAlreadyUsed:
                errors["email"] = "An account with this e-mail address already exists. Log in instead."
        if errors:
            return render_template("account/register.html", name=name, email=email, next=next_page,
                                   errors=errors), 400
        log_in(user)                                         # keeps the cart (plan 2, P2-9)
        flash(f"Welcome, {user.name}. Your account is ready.", "success")
        return redirect(safe_next(next_page))
    return render_template("account/register.html", name="", email="", next=next_page, errors={})


# ---- the order form (plan 3, P3-2 to P3-7, P3-10) --------------------------------------------------------
@bp.route("/order", methods=["GET", "POST"])
@login_required
def order():
    if g.user.is_admin:
        abort(403, description="Staff accounts cannot place orders. Log in as a customer.")      # P3-10
    key = request.form.get("submission_key", "") if request.method == "POST" else secrets.token_hex(16)
    if request.method == "POST":
        if not re.fullmatch(r"[0-9a-f]{32}", key):
            abort(400, description="The form is incomplete. Please open the order form again.")
        earlier = repos().orders.get_by_submission_key(key)
        if earlier is not None:                              # the same form again: show the first order (P3-7)
            if earlier.customer_id != g.user.id:
                abort(404)
            return redirect(url_for("account.order_page", order_id=earlier.id))

    lines, problem = _cart_lines()
    if problem:
        return problem
    values, errors = {}, {}
    if request.method == "POST":
        new_order, errors = order_from_form(request.form, date.today(), [line.item for line in lines])
        if not errors:
            new_order.customer_id, new_order.submission_key = g.user.id, key
            new_order.lines = order_lines_from(lines)        # today's prices are copied in (V7)
            new_order.submitted_at = datetime.now().replace(microsecond=0)
            stored = repos().orders.add(new_order)           # order, lines and groups in one transaction (P3-6)
            session.pop("cart", None)
            flash("Thank you! We have received your booking request.", "success")
            return redirect(url_for("account.order_page", order_id=stored.id))
        values = request.form
    today = date.today()
    page = render_template("account/order_form.html", lines=lines, total=estimated_total_nok(lines),
                           values=values, errors=errors, key=key, events=EVENTS, group_rows=GROUP_ROWS,
                           max_guests=MAX_GUESTS, min_date=today, max_date=today + timedelta(days=MAX_DAYS_AHEAD))
    return page, (400 if errors else 200)


@bp.route("/orders")
@login_required
def my_orders():
    return render_template("account/my_orders.html", orders=repos().orders.list_for_customer(g.user.id),
                           events=EVENTS, statuses=STATUS_NAMES, payments=PAYMENT_NAMES)         # C4, plan 4


@bp.route("/orders/<int:order_id>")
@login_required
def order_page(order_id):
    return _order_page(_own_order(order_id))


@bp.route("/orders/<int:order_id>/questions", methods=["POST"])
@login_required
def ask(order_id):
    if g.user.is_admin:
        abort(403, description="Staff accounts cannot ask questions. Answer them in the admin panel.")   # P5-4
    found = _own_order(order_id)
    try:
        text = validate_question(request.form.get("text", ""))
    except QuestionError as error:
        return _order_page(found, question=request.form.get("text", ""), question_error=str(error)), 400
    repos().questions.add(Question(order_id=found.id, customer_id=g.user.id, text=text,
                                   asked_at=datetime.now().replace(microsecond=0)))
    flash("Your question has been sent. Ekte Mat's answer will appear here.", "success")
    return redirect(url_for("account.order_page", order_id=found.id, _anchor="questions"))


def _own_order(order_id):
    found = repos().orders.get(order_id)
    if found is None or found.customer_id != g.user.id:
        abort(404)                                           # P3-9, P5-4: never confirm that someone else's order exists
    return found


def _order_page(found, question="", question_error=""):
    return render_template("account/order.html", order=found, events=EVENTS, statuses=STATUS_NAMES,
                           payments=PAYMENT_NAMES, question=question, question_error=question_error,
                           max_question=MAX_QUESTION)


def _cart_lines():
    """Today's cart lines, or a redirect if the cart cannot be ordered as it is (P3-6; plan 0, D8)."""
    cart = Cart.from_session(session.get("cart"))
    lines, removed = cart.lines({item.id: item for item in repos().food_items.list()})
    if removed:
        session["cart"] = cart.to_session()
        for name in removed:
            flash(f"“{name}” is no longer on the menu and was removed from your cart." if name else
                  "A dish in your cart is no longer on the menu and was removed.", "error")
        return lines, redirect(url_for("shop.cart"))
    if not lines:
        flash("Your cart is empty. Choose dishes from the menu first.", "error")
        return lines, redirect(url_for("shop.index"))
    below = [line for line in lines if line.below_minimum]
    if below:
        for line in below:
            flash(f"The minimum order for “{line.item.name}” is now {line.item.min_order_qty} portions. "
                  "Change the number in your cart.", "error")
        return lines, redirect(url_for("shop.cart"))
    return lines, None
