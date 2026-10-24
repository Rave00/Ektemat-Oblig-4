"""Admin panel for Ekte Mat staff: food items and pictures (A1, A2, plan 1), orders (A3, plan 4), questions (A4, plan 5).

Every route is protected by @admin_required. The routes only translate between HTTP and the model: the rules are in
app/models/domain.py and app/models/order_status.py, the picture handling in app/models/images.py.
"""
from dataclasses import replace
from datetime import datetime

from flask import Blueprint, abort, flash, g, redirect, render_template, request, session, url_for

from ..models.domain import (ALLERGENS, DIETARY_LABELS, EVENTS, MAX_ANSWER, PAYMENT_NAMES, STATUS_NAMES, FoodItem,
                             QuestionError, answer_question, date_filter, publish_problems, reply_stats,
                             validate_food_item, waiting_time, waiting_too_long)
from ..models.images import ImageError
from ..models.order_status import ACTIONS, NEEDS_REASON, StatusError, change_status, check_payment_status, next_statuses
from . import images, repos
from .security import admin_required

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
@admin_required
def index():
    items = repos().food_items.list()
    orders, now = repos().orders.list(), datetime.now()
    return render_template("admin/index.html",
                           item_count=len(items),
                           published_count=sum(1 for item in items if item.published),
                           waiting=sum(1 for order in orders if order.status == "submitted"),
                           late=sum(1 for order in orders if waiting_too_long(order, now)),
                           months=reply_stats(orders),
                           questions_waiting=len(repos().questions.list("waiting")))


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
# ---- orders (A3, plan 4) ---------------------------------------------------------------------------------
@bp.route("/orders")
@admin_required
def orders():
    status = request.args.get("status") or None
    if status is not None and status not in STATUS_NAMES:
        abort(404)                                        # P4-6: never an unfiltered list for a mistyped filter
    date_from_text, date_to_text = request.args.get("date_from", ""), request.args.get("date_to", "")
    date_from, date_to, problem = date_filter(date_from_text, date_to_text)
    in_range = [] if problem else repos().orders.list(date_from=date_from, date_to=date_to)
    shown = [] if problem else repos().orders.list(status, date_from, date_to)
    counts = {code: sum(1 for order in in_range if order.status == code) for code in STATUS_NAMES}
    now = datetime.now()
    return render_template("admin/orders.html", orders=shown, counts=counts, total=len(in_range), status=status,
                           date_from=date_from_text, date_to=date_to_text, problem=problem,
                           late={order.id for order in shown if waiting_too_long(order, now)},
                           statuses=STATUS_NAMES, payments=PAYMENT_NAMES, events=EVENTS)


@bp.route("/orders/<int:order_id>")
@admin_required
def order(order_id):
    return _order_page(_get_order(order_id))


def _order_page(found, answer_errors=None, answer_texts=None):
    return render_template("admin/order.html", order=found, next_statuses=next_statuses(found.status),
                           actions=ACTIONS, needs_reason=NEEDS_REASON, statuses=STATUS_NAMES, payments=PAYMENT_NAMES,
                           events=EVENTS, late=waiting_too_long(found, datetime.now()), max_answer=MAX_ANSWER,
                           answer_errors=answer_errors or {}, answer_texts=answer_texts or {})


@bp.route("/orders/<int:order_id>/status", methods=["POST"])
@admin_required
def order_status(order_id):
    found = _get_order(order_id)
    back = redirect(url_for("admin.order", order_id=order_id))
    expected = request.form.get("expected_status", "")
    if expected != found.status:                          # 1. the page was older than the order (P4-4)
        flash(_changed_meanwhile(found), "error")
        return back
    try:                                                  # 2. the state machine decides (P4-1 to P4-3)
        changed = change_status(found, request.form.get("status", ""), datetime.now().replace(microsecond=0),
                                request.form.get("reason", ""))
    except StatusError as error:
        flash(str(error), "error")
        return back
    if repos().orders.update_status(changed, expected_status=expected):     # 3. saved only if still `expected`
        flash(f"Order {found.number} is now {STATUS_NAMES[changed.status]}.", "success")
    else:
        flash(_changed_meanwhile(repos().orders.get(order_id)), "error")
    return back


@bp.route("/orders/<int:order_id>/payment", methods=["POST"])
@admin_required
def order_payment(order_id):
    found = _get_order(order_id)
    value = request.form.get("payment_status", "")
    try:
        check_payment_status(value)
    except StatusError as error:
        flash(str(error), "error")
    else:
        repos().orders.update_payment_status(found.id, value)
        flash(f"Payment status of order {found.number}: {PAYMENT_NAMES[value]}.", "success")
    return redirect(url_for("admin.order", order_id=order_id))


# ---- questions (A4, plan 5) ---------------------------------------------------------------------------------
SHOW = {"waiting": "Waiting", "answered": "Answered", "all": "All"}


@bp.route("/questions")
@admin_required
def questions():
    show = request.args.get("show", "waiting")
    if show not in SHOW:
        abort(404)                                        # P5-7: a mistyped filter never shows a different list
    shown, everything = repos().questions.list(show), repos().questions.list("all")
    waiting = sum(1 for question in everything if not question.answered)
    counts = {"waiting": waiting, "answered": len(everything) - waiting, "all": len(everything)}
    now = datetime.now()
    return render_template("admin/questions.html", questions=shown, show=show, shows=SHOW, counts=counts,
                           waited={q.id: waiting_time(q.asked_at, now) for q in shown if not q.answered})


@bp.route("/questions/<int:question_id>/answer", methods=["POST"])
@admin_required
def answer(question_id):
    question = repos().questions.get(question_id)
    if question is None:
        abort(404)
    typed = request.form.get("answer", "")
    try:
        answered = answer_question(question, typed, g.user.id, datetime.now().replace(microsecond=0))
    except QuestionError as error:
        if question.answered:                             # answered from another tab or by another staff member
            flash(str(error), "error")
            return redirect(url_for("admin.order", order_id=question.order_id, _anchor="questions"))
        return _order_page(_get_order(question.order_id), answer_errors={question.id: str(error)},
                           answer_texts={question.id: typed}), 400
    if repos().questions.save_answer(answered):
        flash(f"Your answer to the question on order {question.order_number} has been saved.", "success")
    else:
        flash("This question has already been answered; the first answer is kept.", "error")
    return redirect(url_for("admin.order", order_id=question.order_id, _anchor="questions"))


def _get_order(order_id):
    found = repos().orders.get(order_id)
    if found is None:
        abort(404)
    return found


def _changed_meanwhile(current):
    return (f"Order {current.number} was changed in the meantime: it is now {STATUS_NAMES[current.status]}. "
            "Nothing was saved; check the order before you change it again.")


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
