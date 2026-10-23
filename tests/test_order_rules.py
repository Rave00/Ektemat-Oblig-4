"""Model rules of plan 3 (P3-1, P3-3 to P3-5, P3-8; rules V1-V10), tested without Flask or a database."""
from datetime import date, datetime, timedelta

import pytest

from app.models.cart import CartLine, order_lines_from
from app.models.domain import Order, OrderLine, order_from_form, order_number, validate_registration
from conftest import make_item

TODAY = date(2026, 10, 23)


def form(**changes):
    """A valid order form as the browser sends it (all values are text)."""
    values = {"event_type": "conference", "event_date": "2026-11-20", "guest_count": "40",
              "delivery_street": "Bryggen 1", "delivery_postcode": "5003", "delivery_city": "Bergen"}
    values.update(changes)
    return values


def group(n, description="Nut allergy", size="2", allergies="Tree nuts", diet=""):
    return {f"group_description_{n}": description, f"group_size_{n}": size,
            f"group_allergies_{n}": allergies, f"group_diet_{n}": diet}


def errors_of(values, dishes=None):
    return order_from_form(values, TODAY, dishes or [make_item()])[1]


# ---- registration (P3-1) -------------------------------------------------------------------------------
def test_a_complete_registration_is_valid():
    assert validate_registration("Kari Nordmann", "kari@test.example", "ten-chars!", "ten-chars!") == {}


@pytest.mark.parametrize("name, email, password, again, field", [
    ("", "kari@test.example", "ten-chars!", "ten-chars!", "name"),
    ("x" * 101, "kari@test.example", "ten-chars!", "ten-chars!", "name"),
    ("Kari", "kari.test.example", "ten-chars!", "ten-chars!", "email"),
    ("Kari", "kari@localhost", "ten-chars!", "ten-chars!", "email"),
    ("Kari", "a@b@test.example", "ten-chars!", "ten-chars!", "email"),
    ("Kari", "k" * 250 + "@t.example", "ten-chars!", "ten-chars!", "email"),
    ("Kari", "kari@test.example", "nine-char", "nine-char", "password"),
    ("Kari", "kari@test.example", "x" * 201, "x" * 201, "password"),
    ("Kari", "kari@test.example", "ten-chars!", "ten-chars?", "password_again"),
], ids=["no-name", "long-name", "no-at", "no-dot", "two-ats", "too-long", "short-password", "long-password",
        "different"])
def test_each_broken_registration_rule_is_reported_on_its_field(name, email, password, again, field):
    assert field in validate_registration(name, email, password, again)


# ---- the order form (P3-3) -----------------------------------------------------------------------------
def test_a_complete_form_becomes_an_order():
    order, errors = order_from_form(form(**group(1)), TODAY, [make_item()])
    assert errors == {}
    assert (order.event_type, order.event_date, order.guest_count) == ("conference", date(2026, 11, 20), 40)
    assert (order.delivery_street, order.delivery_postcode, order.delivery_city) == ("Bryggen 1", "5003", "Bergen")
    assert [(g.description, g.size, g.allergy_notes, g.diet_notes) for g in order.groups] == [
        ("Nut allergy", 2, "Tree nuts", "")]


@pytest.mark.parametrize("changes, field", [
    ({"event_type": ""}, "event_type"),                                   # V4
    ({"event_type": "funeral"}, "event_type"),
    ({"event_date": ""}, "event_date"),
    ({"event_date": "2026-13-01"}, "event_date"),
    ({"event_date": "2026-10-22"}, "event_date"),                         # V9: yesterday
    ({"event_date": str(TODAY + timedelta(days=731))}, "event_date"),     # more than two years ahead
    ({"guest_count": "0"}, "guest_count"),                                # V5
    ({"guest_count": "401"}, "guest_count"),                              # V6
    ({"guest_count": "forty"}, "guest_count"),
    ({"delivery_street": " "}, "delivery_street"),
    ({"delivery_street": "x" * 101}, "delivery_street"),
    ({"delivery_postcode": "50O7"}, "delivery_postcode"),                 # V10: the letter O
    ({"delivery_postcode": "5 011"}, "delivery_postcode"),                # V10: a space
    ({"delivery_postcode": "501"}, "delivery_postcode"),
    ({"delivery_city": ""}, "delivery_city"),
], ids=["no-event", "unknown-event", "no-date", "not-a-date", "yesterday", "too-far-ahead", "zero-guests",
        "401-guests", "guests-text", "no-street", "long-street", "postcode-letter", "postcode-space",
        "postcode-short", "no-place"])
def test_each_broken_order_rule_is_reported_on_its_field(changes, field):
    assert field in errors_of(form(**changes))


@pytest.mark.parametrize("changes", [
    {"event_date": str(TODAY)}, {"event_date": str(TODAY + timedelta(days=730))},
    {"guest_count": "1"}, {"guest_count": "400"}, {"delivery_postcode": " 5003 "},
], ids=["today", "two-years-ahead", "one-guest", "400-guests", "postcode-with-spaces-around"])
def test_boundary_values_are_allowed(changes):
    assert errors_of(form(**changes)) == {}


# ---- guest groups (P3-4) -------------------------------------------------------------------------------
def test_empty_group_rows_are_ignored():
    order, errors = order_from_form(form(**group(1, "", "", "", ""), **group(3)), TODAY, [make_item()])
    assert errors == {} and [g.description for g in order.groups] == ["Nut allergy"]


@pytest.mark.parametrize("row", [
    group(2, description=""), group(2, size=""), group(2, size="0"), group(2, size="two"),
    group(2, allergies="x" * 301), group(2, diet="x" * 301), group(2, description="x" * 101),
], ids=["no-description", "no-size", "size-zero", "size-text", "long-allergies", "long-diet", "long-description"])
def test_a_half_filled_or_wrong_group_row_is_refused(row):
    assert "group_2" in errors_of(form(**row))


def test_groups_cannot_have_more_guests_than_the_order():
    errors = errors_of(form(guest_count="10", **group(1, size="6"), **group(2, "Vegans", "5", "", "Vegan")))
    assert errors == {"groups": "The guest groups have 11 guests, but the order is for 10."}


def test_only_the_five_rows_on_the_form_are_read():
    order, _ = order_from_form(form(**group(6)), TODAY, [make_item()])
    assert order.groups == []


# ---- every dish must be offered for the chosen event (P3-5) ---------------------------------------------
def test_a_dish_not_offered_for_the_event_is_named():
    buffet = make_item(name="Julebord buffet", events=["julebord"])
    errors = errors_of(form(event_type="wedding"), dishes=[make_item(events=["wedding"]), buffet])
    assert errors == {"event_type": "Julebord buffet is not offered for Wedding."}


# ---- order number, lines and total (P3-6, P3-8; V7, V8) ------------------------------------------------
def test_the_order_number_is_the_year_and_the_id():
    assert order_number(7, datetime(2026, 10, 23, 10, 30)) == "26-0007"
    assert order_number(12345, datetime(2027, 1, 2)) == "27-12345"


def test_order_lines_copy_todays_price_and_the_total_is_their_sum():
    soup, buffet = make_item(price_nok=189), make_item(name="Buffet", price_nok=595, min_order_qty=20)
    soup.id, buffet.id = 1, 2
    lines = order_lines_from([CartLine(soup, 10), CartLine(buffet, 20)])
    assert [(l.food_item_id, l.quantity, l.unit_price_nok) for l in lines] == [(1, 10, 189), (2, 20, 595)]
    order = Order(customer_id=1, event_type="conference", event_date=TODAY, guest_count=20,
                  delivery_street="Bryggen 1", delivery_postcode="5003", delivery_city="Bergen", lines=lines)
    assert order.total_nok == 13790
    assert OrderLine(1, "Soup", 3, 100).total_nok == 300
