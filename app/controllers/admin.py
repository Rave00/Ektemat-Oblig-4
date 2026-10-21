"""Admin panel for Ekte Mat staff: food items and pictures (A1, A2, plan 1). Orders and questions follow in plans 4-5.

Every route is protected by @admin_required. The routes only translate between HTTP and the model:
the rules are in app/models/domain.py, the picture handling in app/models/images.py.
"""
from dataclasses import replace

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from ..models.domain import (ALLERGENS, DIETARY_LABELS, EVENTS, FoodItem, publish_problems,
                             validate_food_item)
from ..models.images import ImageError
from . import images, repos
from .security import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def index():
    items = repos().food_items.list()
    return render_template("admin/index.html",
                           item_count=len(items),
                           published_count=sum(1 for item in items if item.published))


# ---- food items (A1) ------------------------------------------------------------------------------------
@bp.route("/items")
@admin_required
def items():
    return render_template("admin/items.html", items=repos().food_items.list(), events=EVENTS)


@bp.route("/items/new", methods=["GET", "POST"])
@admin_required
def new_item():
    if request.method == "POST":
        item, errors = _item_from_form(FoodItem(name="", description="", price_nok=0, min_order_qty=1))
        if errors:
            return _form(None, request.form, errors), 400
        item = repos().food_items.add(item)                     # new items start unpublished (P1-3)
        flash(f"Added “{item.name}”. Now add a picture, then publish it.", "success")
        return redirect(url_for("admin.edit_item", item_id=item.id))
    return _form(None, {}, {})


@bp.route("/items/<int:item_id>/edit", methods=["GET", "POST"])
@admin_required
def edit_item(item_id):
    item = _get_item(item_id)
    if request.method == "POST":
        updated, errors = _item_from_form(item)
        updated.published = request.form.get("published") == "on"
        if updated.published and publish_problems(updated):
            errors["published"] = "Cannot publish: " + "; ".join(publish_problems(updated)) + "."
        if errors:
            return _form(item, request.form, errors), 400
        repos().food_items.update(updated)
        flash(f"Saved “{updated.name}”.", "success")
        return redirect(url_for("admin.items"))
    return _form(item, _values_of(item), {})


@bp.route("/items/<int:item_id>/publish", methods=["POST"])
@admin_required
def publish(item_id):
    item = _get_item(item_id)
    problems = publish_problems(item)
    if problems:
        flash(f"“{item.name}” was not published: {'; '.join(problems)}.", "error")
    else:
        item.published = True
        repos().food_items.update(item)
        flash(f"“{item.name}” is now on the menu.", "success")
    return redirect(url_for("admin.items"))


@bp.route("/items/<int:item_id>/unpublish", methods=["POST"])
@admin_required
def unpublish(item_id):
    item = _get_item(item_id)
    item.published = False
    repos().food_items.update(item)
    flash(f"“{item.name}” is hidden from the menu.", "success")
    return redirect(url_for("admin.items"))


@bp.route("/items/<int:item_id>/delete", methods=["POST"])
@admin_required
def delete_item(item_id):
    item = _get_item(item_id)
    if repos().food_items.is_ordered(item.id):                  # P1-6: old orders keep their dishes
        flash(f"“{item.name}” is part of an order and cannot be deleted. Unpublish it instead.", "error")
    else:
        repos().food_items.delete(item.id)
        images().delete(item.image_path)
        flash(f"Deleted “{item.name}”.", "success")
    return redirect(url_for("admin.items"))


# ---- pictures (A2): upload -> preview -> save or discard ------------------------------------------------
@bp.route("/items/<int:item_id>/image", methods=["POST"])
@admin_required
def upload_image(item_id):
    item = _get_item(item_id)
    upload = request.files.get("image")
    if not upload or not upload.filename:
        flash("Choose a picture to upload.", "error")
        return redirect(url_for("admin.edit_item", item_id=item.id))
    try:
        name = images().save_pending(upload.stream)
    except ImageError as problem:
        flash(str(problem), "error")
        return redirect(url_for("admin.edit_item", item_id=item.id))
    previous = _pending().get(str(item.id))
    if previous:
        images().discard_pending(previous)
    _set_pending(item.id, name)
    return redirect(url_for("admin.preview_image", item_id=item.id))


@bp.route("/items/<int:item_id>/image/preview")
@admin_required
def preview_image(item_id):
    item = _get_item(item_id)
    name = _pending().get(str(item.id))
    if not name:
        flash("There is no new picture to preview. Upload one first.", "error")
        return redirect(url_for("admin.edit_item", item_id=item.id))
    return render_template("admin/image_preview.html", item=item, new_image=images().pending_path(name))


@bp.route("/items/<int:item_id>/image/save", methods=["POST"])
@admin_required
def save_image(item_id):
    item = _get_item(item_id)
    name = _set_pending(item.id, None)
    if not name:
        return redirect(url_for("admin.edit_item", item_id=item.id))
    try:
        new_path = images().promote(name)
    except ImageError as problem:
        flash(str(problem), "error")
        return redirect(url_for("admin.edit_item", item_id=item.id))
    old_path, item.image_path = item.image_path, new_path
    repos().food_items.update(item)
    images().delete(old_path)
    flash("The new picture is saved.", "success")
    return redirect(url_for("admin.edit_item", item_id=item.id))


@bp.route("/items/<int:item_id>/image/discard", methods=["POST"])
@admin_required
def discard_image(item_id):
    item = _get_item(item_id)
    name = _set_pending(item.id, None)
    if name:
        images().discard_pending(name)
    flash("The new picture was discarded; nothing changed.", "success")
    return redirect(url_for("admin.edit_item", item_id=item.id))


# ---- helpers ---------------------------------------------------------------------------------------------
def _get_item(item_id):
    item = repos().food_items.get(item_id)
    if item is None:
        abort(404)
    return item


def _item_from_form(base):
    """Turn the submitted form into a FoodItem (a changed copy of `base`) plus any validation errors."""
    form, errors = request.form, {}
    numbers = {}
    for field in ("price_nok", "min_order_qty"):
        try:
            numbers[field] = int(form.get(field, "").strip())
        except ValueError:
            errors[field] = "Enter a whole number."
            numbers[field] = getattr(base, field)
    item = replace(base,
                   name=form.get("name", "").strip(),
                   description=form.get("description", "").strip(),
                   events=form.getlist("events"),
                   allergens=form.getlist("allergens"),
                   labels=form.getlist("labels"),
                   no_allergens=form.get("no_allergens") == "on",
                   **numbers)
    return item, {**validate_food_item(item), **errors}


def _values_of(item):
    """The form's values for an existing item (the same shape as a submitted form)."""
    return {"name": item.name, "description": item.description, "price_nok": item.price_nok,
            "min_order_qty": item.min_order_qty, "events": item.events, "allergens": item.allergens,
            "labels": item.labels, "no_allergens": item.no_allergens, "published": item.published}


def _form(item, values, errors):
    if hasattr(values, "getlist"):          # a submitted form: turn it into the same shape as _values_of()
        values = {**values.to_dict(), "events": values.getlist("events"), "allergens": values.getlist("allergens"),
                  "labels": values.getlist("labels"), "no_allergens": values.get("no_allergens") == "on",
                  "published": values.get("published") == "on"}
    return render_template("admin/item_form.html", item=item, values=values, errors=errors,
                           events=EVENTS, allergens=ALLERGENS, labels=DIETARY_LABELS)


def _pending():
    return session.get("pending_images", {})


def _set_pending(item_id, name):
    """Remember (or with name=None: forget) the pending picture of an item. Returns the previous name."""
    pending = dict(_pending())
    previous = pending.pop(str(item_id), None)
    if name:
        pending[str(item_id)] = name
    session["pending_images"] = pending
    return previous
