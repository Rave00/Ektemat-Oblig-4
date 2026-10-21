"""Model rules for food items (plan 1, P1-1 to P1-3), tested without Flask or a database."""
import pytest

from app.models.domain import (ALLERGEN_INFO_MISSING, PICTURE_MISSING, publish_problems,
                               validate_food_item)
from conftest import make_item


def test_a_complete_item_is_valid():
    assert validate_food_item(make_item()) == {}


@pytest.mark.parametrize("change, field", [
    ({"name": "  "}, "name"),
    ({"name": "x" * 101}, "name"),
    ({"description": ""}, "description"),
    ({"price_nok": -1}, "price_nok"),
    ({"price_nok": 100_001}, "price_nok"),
    ({"min_order_qty": 0}, "min_order_qty"),
    ({"events": []}, "events"),
    ({"events": ["funeral"]}, "events"),
    ({"allergens": ["chocolate"]}, "allergens"),
    ({"labels": ["keto"]}, "labels"),
    ({"allergens": ["milk"], "no_allergens": True}, "allergens"),
])
def test_each_broken_rule_is_reported_on_its_field(change, field):
    assert field in validate_food_item(make_item(**change))


def test_boundary_values_are_allowed():
    assert validate_food_item(make_item(price_nok=0, min_order_qty=1, name="x" * 100)) == {}
    assert validate_food_item(make_item(price_nok=100_000, min_order_qty=1000)) == {}


def test_publishing_needs_allergen_information_and_a_picture():
    assert publish_problems(make_item(allergens=[], image_path=None)) == [ALLERGEN_INFO_MISSING, PICTURE_MISSING]
    assert publish_problems(make_item(allergens=["fish"], image_path="uploads/a.jpg")) == []


def test_contains_no_allergens_counts_as_allergen_information():
    assert publish_problems(make_item(allergens=[], no_allergens=True, image_path="uploads/a.jpg")) == []


def test_the_message_is_the_wording_from_the_backlog():
    assert ALLERGEN_INFO_MISSING == "Allergen information missing"      # lab backlog US-02, criterion 2
