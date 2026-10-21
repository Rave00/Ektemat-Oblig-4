"""Model rules for food items (plan 1, P1-1 to P1-3; plan 2, P2-5, P2-6 and P2-8), tested without Flask or a database."""
import pytest

from app.models.domain import (ALLERGEN_INFO_MISSING, PICTURE_MISSING, menu_sections, publish_problems,
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


# ---- dietary labels that the allergens contradict (plan 2, P2-8) ------------------------------------
@pytest.mark.parametrize("labels, allergens, message", [
    (["vegan"], ["eggs", "milk"], "A vegan dish can't contain Eggs, Milk."),
    (["vegan"], ["molluscs"], "A vegan dish can't contain Molluscs."),
    (["vegetarian"], ["fish", "celery"], "A vegetarian dish can't contain Fish."),
    (["vegetarian"], ["crustaceans"], "A vegetarian dish can't contain Crustaceans."),
    (["gluten_free"], ["gluten"], "A gluten-free dish can't contain Cereals containing gluten."),
], ids=["vegan-eggs-milk", "vegan-molluscs", "vegetarian-fish", "vegetarian-crustaceans", "gluten-free-gluten"])
def test_a_label_that_the_allergens_contradict_is_refused(labels, allergens, message):
    assert validate_food_item(make_item(labels=labels, allergens=allergens)) == {"labels": message}


def test_every_contradicted_label_is_named():
    errors = validate_food_item(make_item(labels=["vegan", "gluten_free"], allergens=["milk", "gluten"]))
    assert errors["labels"] == ("A vegan dish can't contain Milk. "
                                "A gluten-free dish can't contain Cereals containing gluten.")


@pytest.mark.parametrize("labels, allergens", [
    (["vegan"], ["nuts", "soybeans", "sesame"]),
    (["vegetarian"], ["eggs", "milk"]),                    # eggs and milk are fine for vegetarians
    (["gluten_free"], ["milk"]),
    (["lactose_free"], ["milk"]),                          # lactose-free milk still contains milk protein
    (["halal"], ["milk", "eggs", "fish"]),                 # the allergen list cannot prove halal wrong
], ids=["vegan", "vegetarian", "gluten-free", "lactose-free", "halal"])
def test_labels_that_the_allergens_allow_are_accepted(labels, allergens):
    assert validate_food_item(make_item(labels=labels, allergens=allergens)) == {}


def test_every_seed_dish_passes_the_rules():
    from seed import FOOD
    for name, description, price, minimum, events, allergens, labels, published, _ in FOOD:
        item = make_item(name=name, description=description, price_nok=price, min_order_qty=minimum,
                         events=events, allergens=allergens, labels=labels, published=published)
        assert validate_food_item(item) == {}, name


# ---- the customer menu (plan 2, P2-5 and P2-6) --------------------------------------------------------
def test_menu_sections_follow_the_event_order_and_skip_empty_events():
    salmon = make_item(name="Salmon", events=["birthday", "wedding"])
    hidden = make_item(name="Hidden", events=["conference"], published=False)
    assert [(code, [i.name for i in dishes]) for code, _, dishes in menu_sections([salmon, hidden])] == [
        ("wedding", ["Salmon"]), ("birthday", ["Salmon"])]


def test_menu_sections_filter_on_event_and_label():
    salad = make_item(name="Salad", events=["conference", "birthday"], labels=["gluten_free"], allergens=["milk"])
    lamb = make_item(name="Lamb", events=["conference"], allergens=["gluten"])
    assert [code for code, _, _ in menu_sections([salad, lamb], event="birthday")] == ["birthday"]
    assert [i.name for _, _, dishes in menu_sections([salad, lamb], label="gluten_free") for i in dishes] == [
        "Salad", "Salad"]


@pytest.mark.parametrize("event, label", [("funeral", None), (None, "keto")])
def test_an_unknown_filter_raises_instead_of_showing_everything(event, label):
    with pytest.raises(ValueError):
        menu_sections([make_item()], event=event, label=label)
