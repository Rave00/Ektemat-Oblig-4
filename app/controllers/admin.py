"""Admin panel for Ekte Mat staff (A1-A4). Plan 0 only has the dashboard; features follow in plans 1, 4 and 5."""
from flask import Blueprint, render_template

from . import repos
from .security import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def index():
    items = repos().food_items.list()
    return render_template("admin/index.html",
                           item_count=len(items),
                           published_count=sum(1 for item in items if item.published))
