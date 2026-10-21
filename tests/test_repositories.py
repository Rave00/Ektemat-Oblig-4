import sqlite3

import pytest

from app.models.domain import User
from conftest import make_item


def test_user_is_found_by_email_regardless_of_case(repos):
    added = repos.users.add(User(email=" Kari@Test.Example ", name="Kari", role="customer", password_hash="x"))
    found = repos.users.get_by_email("KARI@test.example")
    assert found == added
    assert found.email == "kari@test.example"


def test_the_same_email_cannot_be_registered_twice(repos):
    repos.users.add(User(email="kari@test.example", name="Kari", role="customer", password_hash="x"))
    with pytest.raises(sqlite3.IntegrityError):
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
