"""Acceptance tests 1-15 of plan 4 (My orders; orders in the admin panel), through HTTP. 16-18: model, seed, database."""
import re
from datetime import date, datetime, timedelta
from html import unescape

import pytest
from werkzeug.security import generate_password_hash

from app.models.domain import GuestGroup, User
from app.models.order_status import ACTIONS
from conftest import log_in, make_item, make_order

NBSP = " "
TODAY = date.today()


def text(response):
    return unescape(response.get_data(as_text=True))


def rows(page):
    """The order numbers in the table rows, in the order they are shown."""
    return re.findall(r'<tr[^>]*data-order="([0-9-]+)"', page)


@pytest.fixture
def soup(repos):
    return repos.food_items.add(make_item(name="Fish soup", price_nok=189, events=["conference", "wedding"]))


@pytest.fixture
def nils(repos):
    return repos.users.add(User(email="nils@test.example", name="Nils Hansen", role="customer",
                                password_hash=generate_password_hash("secret-pw")))


# ---- C4, My orders ------------------------------------------------------------------------------------
def test_p4_at01_my_orders_shows_only_my_orders_newest_first(client, repos, users, nils, soup):
    kari = users["customer"].id
    older = make_order(repos, kari, soup.id, submitted_at=datetime.now() - timedelta(days=3), event_type="wedding")
    newer = make_order(repos, kari, soup.id, submitted_at=datetime.now() - timedelta(hours=1), payment_status="paid")
    other = make_order(repos, nils.id, soup.id)
    log_in(client, "kari@test.example")
    page = text(client.get("/account/orders"))
    assert rows(page) == [newer.number, older.number]
    assert other.number not in page
    for shown in ("Conference", "Wedding", "Submitted", "Paid", "Not paid", f"1{NBSP}890 NOK", str(older.event_date)):
        assert shown in page, shown
    assert f'href="/account/orders/{newer.id}"' in page
    assert 'href="/account/orders"' in text(client.get("/"))                 # "My orders" in the header


def test_p4_at02_visitors_are_asked_to_log_in(client):
    assert client.get("/account/orders").headers["Location"].startswith("/account/login")


def test_p4_at03_the_customer_sees_a_rejection_and_its_reason(client, admin, repos, users, soup):
    placed = make_order(repos, users["customer"].id, soup.id)
    admin.post(f"/admin/orders/{placed.id}/status",
               data={"status": "rejected", "expected_status": "submitted", "reason": "We are fully booked that day."})
    admin.post("/account/logout")
    log_in(client, "kari@test.example")
    assert "Rejected" in text(client.get("/account/orders"))
    page = text(client.get(f"/account/orders/{placed.id}"))
    assert "Rejected" in page and "We are fully booked that day." in page


# ---- A3, the order list --------------------------------------------------------------------------------
def test_p4_at04_staff_see_every_order_sorted_by_event_date(admin, repos, users, nils, soup):
    late = make_order(repos, users["customer"].id, soup.id, event_date=TODAY + timedelta(days=40))
    soon = make_order(repos, nils.id, soup.id, event_date=TODAY + timedelta(days=5), guest_count=12)
    page = text(admin.get("/admin/orders"))
    assert rows(page) == [soon.number, late.number]
    for shown in ("Kari", "Nils Hansen", soon.submitted_at.strftime("%Y-%m-%d %H:%M"), str(soon.event_date),
                  "Submitted", "Not paid", f"1{NBSP}890 NOK", ">12<"):
        assert shown in page, shown


def test_p4_at05_the_status_filter_and_its_counts(admin, repos, users, soup):
    kari = users["customer"].id
    submitted = make_order(repos, kari, soup.id)
    approved = make_order(repos, kari, soup.id, status="approved", first_replied_at=datetime.now())
    make_order(repos, kari, soup.id, status="approved", first_replied_at=datetime.now())
    page = text(admin.get("/admin/orders?status=submitted"))
    assert rows(page) == [submitted.number] and approved.number not in rows(page)
    assert "Submitted (1)" in page and "Approved (2)" in page and "All (3)" in page
    assert admin.get("/admin/orders?status=lost").status_code == 404


def test_p4_at06_the_event_date_filter_alone_and_with_a_status(admin, repos, users, soup):
    kari = users["customer"].id
    early = make_order(repos, kari, soup.id, event_date=TODAY + timedelta(days=10))
    middle = make_order(repos, kari, soup.id, event_date=TODAY + timedelta(days=20), status="approved",
                        first_replied_at=datetime.now())
    make_order(repos, kari, soup.id, event_date=TODAY + timedelta(days=30))
    window = f"date_from={TODAY + timedelta(days=10)}&date_to={TODAY + timedelta(days=20)}"
    assert rows(text(admin.get(f"/admin/orders?{window}"))) == [early.number, middle.number]     # both days included
    assert rows(text(admin.get(f"/admin/orders?{window}&status=approved"))) == [middle.number]
    backwards = text(admin.get(f"/admin/orders?date_from={TODAY + timedelta(days=20)}&date_to={TODAY}"))
    assert "The “from” date is after the “to” date." in backwards and rows(backwards) == []
    impossible = text(admin.get("/admin/orders?date_from=2026-02-30"))
    assert "is not a date" in impossible and rows(impossible) == []


def test_p4_at07_orders_waiting_more_than_24_hours_are_highlighted(admin, repos, users, soup):
    kari = users["customer"].id
    old = make_order(repos, kari, soup.id, submitted_at=datetime.now() - timedelta(hours=25))
    new = make_order(repos, kari, soup.id, submitted_at=datetime.now() - timedelta(hours=1))
    answered = make_order(repos, kari, soup.id, submitted_at=datetime.now() - timedelta(days=3), status="approved",
                          first_replied_at=datetime.now() - timedelta(days=2))
    page = text(admin.get("/admin/orders"))
    highlighted = re.findall(r'<tr class="late" data-order="([0-9-]+)"', page)
    assert highlighted == [old.number] and new.number not in highlighted and answered.number not in highlighted


# ---- A3, the staff order page --------------------------------------------------------------------------
def test_p4_at08_the_staff_page_shows_everything_the_customer_sent(admin, repos, users, soup):
    placed = make_order(repos, users["customer"].id, soup.id,
                        groups=[GuestGroup("Nut allergy", 2, "Tree nuts and peanuts", ""),
                                GuestGroup("Vegans", 4, "", "Vegan")])
    page = text(admin.get(f"/admin/orders/{placed.id}"))
    for shown in ("Kari", "kari@test.example", "Nut allergy", "Tree nuts and peanuts", "Vegans", "Vegan",
                  "Fish soup", "189 NOK", f"1{NBSP}890 NOK", "Bryggen 1", "5003 Bergen", placed.number):
        assert shown in page, shown


@pytest.mark.parametrize("status, buttons", [
    ("submitted", ["Approve", "Reject", "Cancel order"]), ("approved", ["Start preparation", "Cancel order"]),
    ("in_preparation", ["Mark as delivered"]), ("delivered", []), ("rejected", []), ("cancelled", []),
])
def test_p4_at09_only_the_allowed_changes_are_offered(admin, repos, users, soup, status, buttons):
    placed = make_order(repos, users["customer"].id, soup.id, status=status,
                        first_replied_at=None if status == "submitted" else datetime.now())
    page = text(admin.get(f"/admin/orders/{placed.id}"))
    assert re.findall(r'<button type="submit" data-status="[a-z_]+"[^>]*>([^<]+)</button>', page) == buttons
    carried = re.findall(r'<input type="hidden" name="status" value="([a-z_]+)">', page)
    assert [ACTIONS[code] for code in carried] == buttons                        # each form carries its own status


def test_a_form_without_a_status_gets_a_clear_message(admin, repos, users, soup):
    placed = make_order(repos, users["customer"].id, soup.id)
    page = text(admin.post(f"/admin/orders/{placed.id}/status", data={"expected_status": "submitted"},
                           follow_redirects=True))
    assert "Unknown status." in page and repos.orders.get(placed.id).status == "submitted"


def test_p4_at10_approving_stores_the_first_reply_time_once(admin, repos, users, soup):
    placed = make_order(repos, users["customer"].id, soup.id)
    admin.post(f"/admin/orders/{placed.id}/status", data={"status": "approved", "expected_status": "submitted"})
    approved = repos.orders.get(placed.id)
    assert approved.status == "approved" and approved.first_replied_at is not None
    admin.post(f"/admin/orders/{placed.id}/status", data={"status": "in_preparation", "expected_status": "approved"})
    assert repos.orders.get(placed.id).first_replied_at == approved.first_replied_at


def test_p4_at11_rejecting_needs_a_reason(admin, repos, users, soup):
    placed = make_order(repos, users["customer"].id, soup.id)
    page = text(admin.post(f"/admin/orders/{placed.id}/status", follow_redirects=True,
                           data={"status": "rejected", "expected_status": "submitted", "reason": " "}))
    assert "Write a reason for the customer." in page and repos.orders.get(placed.id).status == "submitted"
    admin.post(f"/admin/orders/{placed.id}/status",
               data={"status": "rejected", "expected_status": "submitted", "reason": "Fully booked."})
    rejected = repos.orders.get(placed.id)
    assert (rejected.status, rejected.status_reason) == ("rejected", "Fully booked.")


@pytest.mark.parametrize("current, wanted", [("delivered", "submitted"), ("submitted", "delivered")])
def test_p4_at12_a_forbidden_change_is_refused(admin, repos, users, soup, current, wanted):
    placed = make_order(repos, users["customer"].id, soup.id, status=current,
                        first_replied_at=None if current == "submitted" else datetime.now())
    page = text(admin.post(f"/admin/orders/{placed.id}/status", data={"status": wanted, "expected_status": current},
                           follow_redirects=True))
    assert "cannot become" in page and repos.orders.get(placed.id).status == current


def test_p4_at13_a_stale_page_cannot_change_an_order(admin, repos, users, soup):
    placed = make_order(repos, users["customer"].id, soup.id)
    admin.post(f"/admin/orders/{placed.id}/status", data={"status": "approved", "expected_status": "submitted"})
    page = text(admin.post(f"/admin/orders/{placed.id}/status", follow_redirects=True,     # the old tab
                           data={"status": "rejected", "expected_status": "submitted", "reason": "Fully booked."}))
    assert "changed in the meantime" in page and repos.orders.get(placed.id).status == "approved"


def test_p4_at14_every_payment_status_can_be_set_and_nothing_else(admin, repos, users, soup):
    placed = make_order(repos, users["customer"].id, soup.id)
    for value in ("deposit_paid", "invoiced", "paid", "not_paid"):
        admin.post(f"/admin/orders/{placed.id}/payment", data={"payment_status": value})
        assert repos.orders.get(placed.id).payment_status == value
    page = text(admin.post(f"/admin/orders/{placed.id}/payment", data={"payment_status": "refunded"},
                           follow_redirects=True))
    assert "Unknown payment status" in page and repos.orders.get(placed.id).payment_status == "not_paid"


# (Acceptance test 15, customers and visitors on every /admin/orders page, is test_at10 in test_admin_items.py,
#  which now fills in order ids too.)


def test_the_dashboard_shows_waiting_orders_and_the_reply_table(admin, repos, users, soup):
    kari = users["customer"].id
    make_order(repos, kari, soup.id, submitted_at=datetime.now() - timedelta(hours=30))
    arrived = datetime.now() - timedelta(hours=3)
    make_order(repos, kari, soup.id, submitted_at=arrived, status="approved", first_replied_at=arrived + timedelta(hours=1))
    page = text(admin.get("/admin/"))
    assert "1 waiting for a reply" in page and "1 waiting more than 24 hours" in page
    assert re.search(r"Answered within 24 hours", page)
