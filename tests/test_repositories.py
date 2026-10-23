import sqlite3
from datetime import date, datetime

import pytest

from app.models.domain import GuestGroup, Order, OrderLine, User
from app.models.repositories.base import EmailAlreadyUsed
from conftest import make_item


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
