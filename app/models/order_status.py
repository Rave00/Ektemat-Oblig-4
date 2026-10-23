"""The order state machine (A3; plan 4, P4-1 to P4-5).

From the lab's state machine (docs/design/02_uml_state-order.puml), with the statuses Oblig 4 names (plan 0, D10):
submitted -> approved -> in_preparation -> delivered, and rejected or cancelled on the way.
"""
from dataclasses import replace

from .domain import PAYMENT_NAMES, STATUS_NAMES

ALLOWED = {
    "submitted": ("approved", "rejected", "cancelled"),
    "approved": ("in_preparation", "cancelled"),
    "in_preparation": ("delivered",),
    "delivered": (),
    "rejected": (),
    "cancelled": (),
}
NEEDS_REASON = ("rejected", "cancelled")       # US-19 criterion 2; cancelling: ASSUMPTION (P4-2)
MAX_REASON = 300

# The text on the staff page's button for each change ("one action", US-19).
ACTIONS = {"approved": "Approve", "rejected": "Reject", "cancelled": "Cancel order",
           "in_preparation": "Start preparation", "delivered": "Mark as delivered"}


class StatusError(ValueError):
    """A change the state machine refuses. The message is written for staff."""


def next_statuses(status):
    """The statuses an order can move to from `status`; empty for final statuses."""
    return ALLOWED.get(status, ())


def change_status(order, new_status, now, reason=""):
    """A changed copy of `order` with the new status, or StatusError.

    Leaving "submitted" for the first time stores the first reply time (P4-3, NFR-19); it never changes afterwards.
    """
    if new_status not in STATUS_NAMES:
        raise StatusError("Unknown status.")
    if new_status not in next_statuses(order.status):
        raise StatusError(f"An order that is {STATUS_NAMES[order.status]} cannot become {STATUS_NAMES[new_status]}.")
    reason = reason.strip()
    if new_status in NEEDS_REASON:
        if not reason:
            raise StatusError("Write a reason for the customer.")
        if len(reason) > MAX_REASON:
            raise StatusError(f"The reason can be at most {MAX_REASON} characters.")
    changed = replace(order, status=new_status,
                      status_reason=reason if new_status in NEEDS_REASON else order.status_reason)
    if order.status == "submitted" and order.first_replied_at is None:
        changed.first_replied_at = now
    return changed


def check_payment_status(value):
    """Payment status is independent of the order status and has four values (P4-5)."""
    if value not in PAYMENT_NAMES:
        raise StatusError("Unknown payment status.")
