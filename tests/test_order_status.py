"""The order state machine and the reply-time measurement (plan 4, P4-1 to P4-5), tested without Flask or a database."""
from datetime import date, datetime, timedelta

import pytest

from app.models.domain import Order, reply_stats, waiting_too_long
from app.models.order_status import ALLOWED, StatusError, change_status, check_payment_status, next_statuses

NOW = datetime(2026, 10, 23, 12, 0)


def order(status="submitted", **changes):
    values = dict(customer_id=1, event_type="conference", event_date=date(2026, 11, 20), guest_count=40,
                  delivery_street="Bryggen 1", delivery_postcode="5003", delivery_city="Bergen", status=status,
                  submitted_at=NOW - timedelta(hours=5), id=7)
    values.update(changes)
    return Order(**values)


# ---- which changes are allowed (A3; plan 0, D10) -------------------------------------------------------
def test_the_allowed_changes_are_those_in_a3():
    assert ALLOWED == {"submitted": ("approved", "rejected", "cancelled"), "approved": ("in_preparation", "cancelled"),
                       "in_preparation": ("delivered",), "delivered": (), "rejected": (), "cancelled": ()}


@pytest.mark.parametrize("old, new", [(old, new) for old, nexts in ALLOWED.items() for new in nexts])
def test_every_allowed_change_works(old, new):
    changed = change_status(order(old), new, NOW, reason="Fully booked")
    assert changed.status == new


@pytest.mark.parametrize("old, new", [
    ("submitted", "delivered"), ("submitted", "in_preparation"), ("approved", "submitted"), ("delivered", "submitted"),
    ("rejected", "approved"), ("cancelled", "approved"), ("in_preparation", "cancelled"), ("submitted", "submitted"),
    ("submitted", "lost"),
], ids=["skip-to-delivered", "skip-approval", "back-to-submitted", "delivered-back", "rejected-reopened",
        "cancelled-reopened", "cancel-in-preparation", "same-status", "unknown-status"])
def test_every_other_change_is_refused(old, new):
    with pytest.raises(StatusError):
        change_status(order(old), new, NOW, reason="x")


def test_final_statuses_offer_no_buttons():
    assert [next_statuses(s) for s in ("delivered", "rejected", "cancelled")] == [(), (), ()]
    assert next_statuses("unknown") == ()


def test_the_original_order_is_not_changed():
    original = order()
    change_status(original, "approved", NOW)
    assert original.status == "submitted" and original.first_replied_at is None


# ---- a reason for rejecting and cancelling (P4-2) -------------------------------------------------------
@pytest.mark.parametrize("new", ["rejected", "cancelled"])
def test_rejecting_or_cancelling_needs_a_reason(new):
    with pytest.raises(StatusError, match="reason"):
        change_status(order(), new, NOW, reason="   ")
    with pytest.raises(StatusError, match="300"):
        change_status(order(), new, NOW, reason="x" * 301)
    assert change_status(order(), new, NOW, reason=" We are fully booked. ").status_reason == "We are fully booked."


def test_approving_needs_no_reason_and_stores_none():
    assert change_status(order(), "approved", NOW, reason="ignored").status_reason == ""


# ---- the first reply time (P4-3, NFR-19) ---------------------------------------------------------------
@pytest.mark.parametrize("new", ["approved", "rejected", "cancelled"])
def test_leaving_submitted_stores_the_first_reply_time(new):
    assert change_status(order(), new, NOW, reason="x").first_replied_at == NOW


def test_the_first_reply_time_never_changes_afterwards():
    approved = change_status(order(), "approved", NOW)
    later = change_status(approved, "in_preparation", NOW + timedelta(days=3))
    assert later.first_replied_at == NOW


# ---- payment status (P4-5) -----------------------------------------------------------------------------
@pytest.mark.parametrize("value", ["not_paid", "deposit_paid", "invoiced", "paid"])
def test_the_four_payment_statuses_are_accepted(value):
    check_payment_status(value)


@pytest.mark.parametrize("value", ["", "Paid", "refunded"])
def test_any_other_payment_status_is_refused(value):
    with pytest.raises(StatusError):
        check_payment_status(value)


# ---- waiting more than 24 hours, and the monthly reply table (US-17, NFR-19) -----------------------------
def test_only_submitted_orders_older_than_24_hours_are_waiting_too_long():
    assert waiting_too_long(order(submitted_at=NOW - timedelta(hours=25)), NOW)
    assert not waiting_too_long(order(submitted_at=NOW - timedelta(hours=1)), NOW)
    assert not waiting_too_long(order("approved", submitted_at=NOW - timedelta(days=3)), NOW)


def test_p4_at16_the_reply_table_counts_per_month():
    arrived = datetime(2026, 10, 5, 9, 0)
    orders = [order("approved", submitted_at=arrived, first_replied_at=arrived + timedelta(hours=10)),
              order("rejected", submitted_at=arrived, first_replied_at=arrived + timedelta(hours=30)),
              order("submitted", submitted_at=arrived),
              order("approved", submitted_at=datetime(2026, 11, 2, 8, 0),
                    first_replied_at=datetime(2026, 11, 2, 10, 0))]
    months = reply_stats(orders)
    assert [(m.month, m.within, m.later, m.waiting, m.total) for m in months] == [
        ("2026-11", 1, 0, 0, 1), ("2026-10", 1, 1, 1, 3)]                 # newest month first
    assert months[1].share_within == pytest.approx(1 / 3)


def test_exactly_24_hours_counts_as_within():
    arrived = datetime(2026, 10, 5, 9, 0)
    [month] = reply_stats([order("approved", submitted_at=arrived, first_replied_at=arrived + timedelta(hours=24))])
    assert month.within == 1
