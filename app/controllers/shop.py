"""Customer site: menu and cart (C1, C2). Plan 0 only has the front page; plan 2 builds the menu and cart."""
from flask import Blueprint, render_template

from . import repos

bp = Blueprint("shop", __name__)


@bp.route("/")
def index():
    items = repos().food_items.list(published_only=True)
    return render_template("shop/index.html", items=items)
