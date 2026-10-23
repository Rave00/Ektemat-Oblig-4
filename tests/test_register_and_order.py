"""Acceptance tests 1-15 of plan 3 (register and submit an order), through HTTP. Tests 16-17: repository and model."""
import secrets
from datetime import date, timedelta
from html import unescape

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.domain import User
from conftest import log_in, make_item

NBSP = " "
REGISTER = {"name": "Ola Nordmann", "email": "ola@test.example", "password": "long-enough-pw",
            "password_again": "long-enough-pw"}


def text(response):
    return unescape(response.get_data(as_text=True))


def cart_of(client):
    with client.session_transaction() as session:
        return session.get("cart", {})


def fill_cart(client, item, portions=10):
    client.post("/cart/add", data={"item_id": str(item.id), "portions": str(portions)})


def order_form(**changes):
    values = {"event_type": "conference", "event_date": str(date.today() + timedelta(days=30)), "guest_count": "40",
              "delivery_street": "Bryggen 1", "delivery_postcode": "5003", "delivery_city": "Bergen",
              "submission_key": secrets.token_hex(16)}
    values.update(changes)
    return values


GROUPS = {"group_description_1": "Nut allergy", "group_size_1": "2", "group_allergies_1": "Tree nuts",
          "group_description_2": "Vegans", "group_size_2": "5", "group_diet_2": "Vegan"}


@pytest.fixture
def soup(repos):
    return repos.food_items.add(make_item(name="Fish soup", price_nok=189, min_order_qty=10,
                                          events=["conference", "corporate_lunch"], image_path="uploads/soup.jpg"))


@pytest.fixture
def customer(client, users):
    """A test client logged in as the customer Kari."""
    log_in(client, "kari@test.example")
    return client


# ---- register (US-47) ---------------------------------------------------------------------------------
def test_p3_at01_a_visitor_registers_and_is_logged_in(client, repos):
    response = client.post("/account/register", data={**REGISTER, "next": "/cart"})
    assert response.status_code == 302 and response.headers["Location"] == "/cart"
    user = repos.users.get_by_email("ola@test.example")
    assert user.role == "customer" and user.name == "Ola Nordmann"
    assert "long-enough-pw" not in user.password_hash                    # stored only as a hash
    assert "Ola Nordmann" in text(client.get("/"))                       # logged in: the name is in the header


def test_p3_at02_wrong_fields_are_shown_and_nothing_is_stored(client, repos):
    bad = {**REGISTER, "name": "", "email": "ola.test.example", "password": "nine-char", "password_again": "other"}
    response = client.post("/account/register", data=bad)
    page = text(response)
    assert response.status_code == 400
    for message in ("Enter your name.", "Enter an e-mail address", "at least 10 characters", "not the same"):
        assert message in page, message
    assert 'value="ola.test.example"' in page and "nine-char" not in page   # e-mail kept, password never echoed
    assert repos.users.get_by_email("ola.test.example") is None


def test_p3_at03_an_e_mail_address_can_only_be_registered_once(client, repos, users):
    response = client.post("/account/register", data={**REGISTER, "email": "KARI@test.example"})
    assert response.status_code == 400
    assert "An account with this e-mail address already exists." in text(response)
    assert repos.users.get_by_email("kari@test.example").name == "Kari"


def test_p3_at04_a_tampered_role_field_still_makes_a_customer(client, repos):
    client.post("/account/register", data={**REGISTER, "role": "admin"})
    assert repos.users.get_by_email("ola@test.example").role == "customer"


# ---- the way in (US-47, criterion 3) --------------------------------------------------------------------
def test_p3_at05_a_visitor_with_a_cart_registers_and_reaches_the_order_form(client, soup):
    fill_cart(client, soup)
    assert "Send booking request" in text(client.get("/cart"))
    response = client.get("/account/order")
    assert response.status_code == 302 and response.headers["Location"].startswith("/account/login?next=/account/order")
    login_page = text(client.get(response.headers["Location"]))
    assert 'href="/account/register?next=/account/order"' in login_page
    response = client.post("/account/register", data={**REGISTER, "next": "/account/order"})
    assert response.headers["Location"] == "/account/order"
    form_page = text(client.get("/account/order"))
    assert "Fish soup" in form_page and f"1{NBSP}890 NOK" in form_page
    assert cart_of(client) == {str(soup.id): 10}


# ---- the order form and submitting (C3, US-09, US-40) --------------------------------------------------
def test_p3_at06_a_valid_order_is_stored_and_shown(customer, repos, users, soup):
    fill_cart(customer, soup, 12)
    response = customer.post("/account/order", data=order_form(**GROUPS))
    assert response.status_code == 302
    order_id = int(response.headers["Location"].rsplit("/", 1)[1])
    order = repos.orders.get(order_id)
    assert (order.customer_id, order.status, order.payment_status) == (users["customer"].id, "submitted", "not_paid")
    assert [(l.food_item_id, l.quantity, l.unit_price_nok) for l in order.lines] == [(soup.id, 12, 189)]
    assert [(g.description, g.size) for g in order.groups] == [("Nut allergy", 2), ("Vegans", 5)]
    assert cart_of(customer) == {}
    page = text(customer.get(response.headers["Location"]))
    assert f"{date.today():%y}-{order_id:04d}" in page and f"2{NBSP}268 NOK" in page      # 12 x 189
    assert "Nut allergy" in page and "Tree nuts" in page and "Submitted" in page and "Not paid" in page


@pytest.mark.parametrize("changes, message", [
    ({"event_type": ""}, "Choose the kind of event."),
    ({"event_date": str(date.today() - timedelta(days=1))}, "The event date cannot be in the past."),
    ({"event_date": str(date.today() + timedelta(days=731))}, "at most two years ahead"),
    ({"guest_count": "0"}, "between 1 and 400"),
    ({"guest_count": "401"}, "between 1 and 400"),
    ({"delivery_postcode": "50O7"}, "four digits"),
    ({"delivery_street": ""}, "Enter the street address."),
], ids=["no-event", "yesterday", "too-far-ahead", "zero-guests", "401-guests", "postcode-letter-o", "no-street"])
def test_p3_at07_wrong_fields_are_shown_and_nothing_is_stored(customer, repos, soup, changes, message):
    fill_cart(customer, soup)
    response = customer.post("/account/order", data=order_form(**changes))
    page = text(response)
    assert response.status_code == 400 and message in page
    assert 'value="Bryggen 1"' in page or changes.get("delivery_street") == ""      # the form keeps what was typed
    assert repos.orders.get(1) is None and cart_of(customer) == {str(soup.id): 10}


def test_p3_at08_guest_groups_are_checked_and_have_no_name_field(customer, repos, soup):
    fill_cart(customer, soup)
    page = text(customer.get("/account/order"))
    assert "Do not write guest names" in page and "name=\"group_name" not in page
    response = customer.post("/account/order", data=order_form(guest_count="6", **GROUPS))     # 2 + 5 > 6
    assert response.status_code == 400 and "The guest groups have 7 guests, but the order is for 6." in text(response)
    response = customer.post("/account/order", data=order_form(group_size_3="4"))             # a number, no description
    assert response.status_code == 400
    assert repos.orders.get(1) is None


def test_p3_at09_a_dish_not_offered_for_the_event_is_named(customer, repos, soup):
    fill_cart(customer, soup)
    response = customer.post("/account/order", data=order_form(event_type="wedding"))
    assert response.status_code == 400 and "Fish soup is not offered for Wedding." in text(response)
    assert repos.orders.get(1) is None


def test_p3_at10_a_submitted_order_keeps_its_price(customer, repos, soup):
    fill_cart(customer, soup)
    location = customer.post("/account/order", data=order_form()).headers["Location"]
    soup.price_nok = 249
    repos.food_items.update(soup)
    page = text(customer.get(location))
    assert "189 NOK" in page and f"1{NBSP}890 NOK" in page and "249 NOK" not in page


def test_p3_at11_a_cart_that_changed_is_not_ordered(customer, repos, soup):
    response = customer.post("/account/order", data=order_form())                      # empty cart
    assert response.headers["Location"] == "/" and repos.orders.get(1) is None
    fill_cart(customer, soup)
    soup.min_order_qty = 20
    repos.food_items.update(soup)
    response = customer.post("/account/order", data=order_form(), follow_redirects=True)
    assert "The minimum order for “Fish soup” is now 20 portions" in text(response)
    soup.min_order_qty, soup.published = 10, False
    repos.food_items.update(soup)
    response = customer.post("/account/order", data=order_form(), follow_redirects=True)
    assert "“Fish soup” is no longer on the menu" in text(response)
    assert repos.orders.get(1) is None


def test_p3_at12_the_same_form_twice_gives_one_order(customer, repos, soup):
    fill_cart(customer, soup)
    form = order_form()
    first = customer.post("/account/order", data=form)
    second = customer.post("/account/order", data=form)                                # double click, cart now empty
    assert first.headers["Location"] == second.headers["Location"]
    assert repos.orders.get(1) is not None and repos.orders.get(2) is None


def test_p3_at13_an_order_page_is_only_for_its_customer(client, customer, repos, soup):
    fill_cart(customer, soup)
    location = customer.post("/account/order", data=order_form()).headers["Location"]
    repos.users.add(User(email="nils@test.example", name="Nils", role="customer",
                         password_hash=generate_password_hash("secret-pw")))
    other = client.application.test_client()
    log_in(other, "nils@test.example")
    assert other.get(location).status_code == 404
    visitor = client.application.test_client()
    assert visitor.get(location).headers["Location"].startswith("/account/login")


def test_p3_at14_staff_accounts_cannot_order(admin, soup):
    fill_cart(admin, soup)
    for response in (admin.get("/account/order"), admin.post("/account/order", data=order_form())):
        assert response.status_code == 403
        assert "Staff accounts cannot place orders. Log in as a customer." in text(response)


def test_p3_at15_register_and_order_forms_need_the_csrf_token(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "csrf.db")})   # CSRF on
    client = app.test_client()
    assert client.post("/account/register", data=REGISTER).status_code == 400
    assert client.post("/account/order", data=order_form()).status_code == 400
    assert app.extensions["repositories"].users.get_by_email("ola@test.example") is None
