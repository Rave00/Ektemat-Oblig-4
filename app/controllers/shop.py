"""Customer site: menu by event and shopping cart (C1, C2, plan 2).

The routes only translate between HTTP and the model: the menu sections come from app/models/domain.py and
the cart rules from app/models/cart.py. The cart is kept in the session as {dish id: portions} (plan 0, D8).
"""
from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from ..models.cart import MAX_PORTIONS, Cart, CartError, estimated_total_nok, parse_portions
from ..models.domain import ALLERGENS, DIETARY_LABELS, EVENTS, menu_sections
from . import repos
from .security import safe_next

bp = Blueprint("shop", __name__)


@bp.app_context_processor
def cart_size():
    """ "Cart (n)" in the header: n is the number of different dishes, not portions (P2-10)."""
    return {"cart_size": len(session.get("cart") or {})}


@bp.route("/")
def index():
    event = request.args.get("event") or None
    label = request.args.get("label") or None
    try:
        sections = menu_sections(repos().food_items.list(published_only=True), event, label)
    except ValueError:
        abort(404)                                         # P2-6: never an unfiltered menu for a mistyped filter
    return render_template("shop/index.html", sections=sections, event=event, label=label,
                           events=EVENTS, labels=DIETARY_LABELS, allergens=ALLERGENS, max_portions=MAX_PORTIONS,
                           here=request.full_path.rstrip("?"))


@bp.route("/cart")
def cart():
    cart = _cart()
    lines, removed = cart.lines({item.id: item for item in repos().food_items.list()})
    if removed:
        _save(cart)                                        # dishes no longer for sale are gone for good (P2-3)
    return render_template("shop/cart.html", lines=lines, removed=removed, total=estimated_total_nok(lines),
                           max_portions=MAX_PORTIONS)


@bp.route("/cart/add", methods=["POST"])
def cart_add():
    item, cart = _posted_item(), _cart()
    try:
        portions = parse_portions(request.form.get("portions", ""))
        cart.add(item, portions)
    except CartError as error:
        flash(str(error), "error")
    else:
        _save(cart)
        flash(f"Added {portions} portions of “{item.name}” to the cart.", "success")
    return redirect(safe_next(request.form.get("next")))


@bp.route("/cart/update", methods=["POST"])
def cart_update():
    item, cart = _posted_item(), _cart()
    try:
        cart.set_quantity(item, parse_portions(request.form.get("portions", "")))
    except CartError as error:
        flash(str(error), "error")
    else:
        _save(cart)
        flash(f"Updated “{item.name}”.", "success")
    return redirect(url_for("shop.cart"))


@bp.route("/cart/remove", methods=["POST"])
def cart_remove():
    item, cart = _posted_item(), _cart()
    if item is not None and item.id in cart.portions:
        cart.remove(item.id)
        _save(cart)
        flash(f"Removed “{item.name}” from the cart.", "success")
    return redirect(url_for("shop.cart"))


# ---- helpers --------------------------------------------------------------------------------------------
def _posted_item():
    """The dish named by the form's item_id, or None for a missing or tampered id."""
    item_id = request.form.get("item_id", "")
    return repos().food_items.get(int(item_id)) if item_id.isdecimal() and len(item_id) < 10 else None


def _cart():
    return Cart.from_session(session.get("cart"))


def _save(cart):
    if cart.portions:
        session["cart"] = cart.to_session()
    else:
        session.pop("cart", None)
