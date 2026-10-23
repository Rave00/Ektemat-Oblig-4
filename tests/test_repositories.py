import sqlite3
from dataclasses import replace
from datetime import date, datetime, timedelta

import pytest

from app.models.domain import GuestGroup, Order, OrderLine, User
from app.models.repositories.base import EmailAlreadyUsed
from conftest import make_item, make_order


def test_user_is_found_by_email_regardless_of_case(repos):
    added = repos.users.add(User(email=" Kari@Test.Example ", name="Kari", role="customer", password_hash="x"))
    found = repos.users.get_by_email("KARI@test.example")
    assert found == added
    assert found.email == "kari@test.example"


def test_the_same_email_cannot_be_registered_twice(repos):
    repos.users.add(User(email="kari@test.example", name="Kari", role="customer", password_hash="x"))
    with pytest.raises(EmailAlreadyUsed):                  # the same error for every storage (plan 6, P6-7)
        repos.users.add(User(email="KARI@test.example", name="Kari 2", role="customer", password_hash="y"))


def test_food_item_round_trip_keeps_events_allergens_and_labels(repos):
    added = repos.food_items.add(make_item(events=["wedding", "birthday"], allergens=["milk", "fish"],
                                           labels=["gluten_free"]))
    loaded = repos.food_items.get(added.id)
    assert loaded == added
    assert loaded.events == ["birthday", "wedding"]
    assert loaded.allergens == ["fish", "milk"]
    assert loaded.labels == ["gluten_free"]


def test_list_can_return_only_published_items(repos):
    repos.food_items.add(make_item(name="Published soup", published=True))
    repos.food_items.add(make_item(name="Hidden soup", published=False))
    assert [i.name for i in repos.food_items.list()] == ["Hidden soup", "Published soup"]
    assert [i.name for i in repos.food_items.list(published_only=True)] == ["Published soup"]


def test_update_replaces_the_lists(repos):
    item = repos.food_items.add(make_item(allergens=["fish", "milk"]))
    item.allergens = ["celery"]
    item.price_nok = 199
    repos.food_items.update(item)
    loaded = repos.food_items.get(item.id)
    assert loaded.allergens == ["celery"] and loaded.price_nok == 199


def test_delete_removes_the_item(repos):
    item = repos.food_items.add(make_item())
    repos.food_items.delete(item.id)
    assert repos.food_items.get(item.id) is None


def test_database_refuses_impossible_values(repos):
    with pytest.raises(sqlite3.IntegrityError):
        repos.food_items.add(make_item(min_order_qty=0))


# ---- orders (plan 3) --------------------------------------------------------------------------------------
def new_order(customer, lines, key="k1", groups=()):
    return Order(customer_id=customer.id, event_type="wedding", event_date=date(2027, 6, 19), guest_count=120,
                 delivery_street="Bryggen 1", delivery_postcode="5003", delivery_city="Bergen",
                 submission_key=key, submitted_at=datetime(2026, 10, 23, 10, 30), lines=list(lines),
                 groups=list(groups))


@pytest.fixture
def customer(repos):
    return repos.users.add(User(email="kari@test.example", name="Kari", role="customer", password_hash="x"))


def test_an_order_is_stored_with_its_lines_and_guest_groups(repos, customer):
    dinner = repos.food_items.add(make_item(name="Wedding dinner", price_nok=875))
    stored = repos.orders.add(new_order(customer, [OrderLine(dinner.id, "", 120, 875)],
                                        groups=[GuestGroup("Nut allergy", 3, "Tree nuts", "")]))
    loaded = repos.orders.get(stored.id)
    assert loaded == stored and loaded.number == "26-%04d" % stored.id
    assert (loaded.status, loaded.payment_status, loaded.event_date) == ("submitted", "not_paid", date(2027, 6, 19))
    assert [(l.name, l.quantity, l.unit_price_nok) for l in loaded.lines] == [("Wedding dinner", 120, 875)]
    assert [(g.description, g.size, g.allergy_notes) for g in loaded.groups] == [("Nut allergy", 3, "Tree nuts")]
    assert loaded.total_nok == 105000
    assert repos.food_items.is_ordered(dinner.id)


def test_p3_at16_an_order_is_stored_completely_or_not_at_all(repos, customer):
    dinner = repos.food_items.add(make_item(name="Wedding dinner"))
    with pytest.raises(Exception):
        repos.orders.add(new_order(customer, [OrderLine(dinner.id, "", 120, 875), OrderLine(9999, "", 10, 100)],
                                   groups=[GuestGroup("Nut allergy", 3)]))
    with repos.db.connect() as conn:
        counts = [conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0] for t in ("orders", "order_lines", "guest_groups")]
    assert counts == [0, 0, 0]


def test_the_same_submission_key_returns_the_first_order(repos, customer):
    dinner = repos.food_items.add(make_item(name="Wedding dinner"))
    first = repos.orders.add(new_order(customer, [OrderLine(dinner.id, "", 120, 875)], key="same"))
    again = repos.orders.add(new_order(customer, [OrderLine(dinner.id, "", 50, 875)], key="same"))
    assert again.id == first.id and [l.quantity for l in again.lines] == [120]
    assert repos.orders.get_by_submission_key("same").id == first.id
    assert repos.orders.get_by_submission_key("other") is None


@pytest.mark.parametrize("changes", [{"guest_count": 401}, {"delivery_postcode": "50O7"}, {"guest_count": 0}],
                         ids=["V6-401-guests", "V10-postcode", "V5-zero-guests"])
def test_the_database_also_refuses_impossible_orders(repos, customer, changes):
    order = new_order(customer, [])
    for name, value in changes.items():
        setattr(order, name, value)
    with pytest.raises(sqlite3.IntegrityError):
        repos.orders.add(order)


# ---- orders in plan 4: lists, status changes, payment, new columns ----------------------------------------
def test_staff_list_has_the_customer_and_is_sorted_by_event_date(repos, customer):
    dish = repos.food_items.add(make_item())
    later = make_order(repos, customer.id, dish.id, event_date=date(2027, 3, 1))
    sooner = make_order(repos, customer.id, dish.id, event_date=date(2027, 1, 1))
    listed = repos.orders.list()
    assert [o.id for o in listed] == [sooner.id, later.id]
    assert (listed[0].customer_name, listed[0].customer_email) == ("Kari", "kari@test.example")
    assert listed[0].total_nok == 1890                     # the lines come with the list


def test_staff_list_filters_on_status_and_event_dates(repos, customer):
    dish = repos.food_items.add(make_item())
    a = make_order(repos, customer.id, dish.id, event_date=date(2027, 1, 1))
    b = make_order(repos, customer.id, dish.id, event_date=date(2027, 1, 15), status="approved",
                   first_replied_at=datetime(2026, 10, 23))
    make_order(repos, customer.id, dish.id, event_date=date(2027, 2, 1))
    assert [o.id for o in repos.orders.list(status="approved")] == [b.id]
    assert [o.id for o in repos.orders.list(date_from=date(2027, 1, 1), date_to=date(2027, 1, 15))] == [a.id, b.id]
    assert [o.id for o in repos.orders.list(date_to=date(2027, 1, 1))] == [a.id]


def test_a_customers_list_is_theirs_only_newest_first(repos, customer):
    dish = repos.food_items.add(make_item())
    other = repos.users.add(User(email="nils@test.example", name="Nils", role="customer", password_hash="x"))
    old = make_order(repos, customer.id, dish.id, submitted_at=datetime(2026, 10, 1, 9, 0))
    new = make_order(repos, customer.id, dish.id, submitted_at=datetime(2026, 10, 20, 9, 0))
    make_order(repos, other.id, dish.id)
    assert [o.id for o in repos.orders.list_for_customer(customer.id)] == [new.id, old.id]


def test_a_status_change_is_saved_only_if_the_status_is_still_the_expected_one(repos, customer):
    dish = repos.food_items.add(make_item())
    stored = make_order(repos, customer.id, dish.id)
    approved = replace(stored, status="approved", first_replied_at=datetime(2026, 10, 23, 12, 0))
    assert repos.orders.update_status(approved, expected_status="submitted") is True
    rejected = replace(stored, status="rejected", status_reason="Too late", first_replied_at=datetime(2026, 10, 23, 13))
    assert repos.orders.update_status(rejected, expected_status="submitted") is False       # someone was faster
    loaded = repos.orders.get(stored.id)
    assert (loaded.status, loaded.status_reason, loaded.first_replied_at) == ("approved", "", datetime(2026, 10, 23, 12))


def test_the_payment_status_is_saved(repos, customer):
    dish = repos.food_items.add(make_item())
    stored = make_order(repos, customer.id, dish.id)
    repos.orders.update_payment_status(stored.id, "deposit_paid")
    assert repos.orders.get(stored.id).payment_status == "deposit_paid"
    with pytest.raises(sqlite3.IntegrityError):
        repos.orders.update_payment_status(stored.id, "refunded")                      # the database refuses it too


def test_p4_at18_the_new_columns_are_added_to_an_old_database(tmp_path):
    from app.models.repositories.sqlite import SqliteRepositories
    path = tmp_path / "plan3.db"
    with sqlite3.connect(path) as conn:                    # the orders table as plan 3 left it
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE, name TEXT NOT NULL,
                                password_hash TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT);
            CREATE TABLE orders (id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, event_type TEXT NOT NULL,
                event_date TEXT NOT NULL, guest_count INTEGER NOT NULL, delivery_street TEXT NOT NULL,
                delivery_postcode TEXT NOT NULL, delivery_city TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'submitted',
                payment_status TEXT NOT NULL DEFAULT 'not_paid', submitted_at TEXT NOT NULL,
                submission_key TEXT NOT NULL UNIQUE);
            INSERT INTO users VALUES (1, 'kari@test.example', 'Kari', 'x', 'customer', NULL);
            INSERT INTO orders (customer_id, event_type, event_date, guest_count, delivery_street, delivery_postcode,
                delivery_city, submitted_at, submission_key)
                VALUES (1, 'wedding', '2027-06-19', 80, 'Bryggen 1', '5003', 'Bergen', '2026-10-22 10:00:00', 'old');
        """)
    repos = SqliteRepositories(path)
    repos.initialise()
    order = repos.orders.get(1)
    assert (order.guest_count, order.status_reason, order.first_replied_at) == (80, "", None)
