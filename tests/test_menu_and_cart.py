"""Acceptance tests 1-17 of plan 2 (customer menu by event and shopping cart), through HTTP."""
from html import unescape
import re

import pytest

from app import create_app
from conftest import log_in, make_item

NBSP = " "                       # the space between thousands in "12 450 NOK" never breaks a line


def page(client, url):
    response = client.get(url)
    assert response.status_code == 200, url
    return response.get_data(as_text=True)


def sections(html):
    """{event code: the HTML of that section} in the order the sections appear on the page."""
    parts = re.split(r'<section class="menu-section" id="([a-z_]+)"', html)
    return dict(zip(parts[1::2], parts[2::2]))


def cart_of(client):
    with client.session_transaction() as session:
        return session.get("cart", {})


def add(client, item, portions, follow=True):
    return client.post("/cart/add", data={"item_id": str(item.id), "portions": str(portions)},
                       follow_redirects=follow)


@pytest.fixture
def soup(repos):
    return repos.food_items.add(make_item(name="Fish soup", description="Creamy soup from Bergen", price_nok=189,
                                          min_order_qty=10, events=["conference", "corporate_lunch"],
                                          allergens=["fish", "milk"], image_path="uploads/soup.jpg"))


@pytest.fixture
def buffet(repos):
    return repos.food_items.add(make_item(name="Julebord buffet", description="Ribs and pinnekjøtt", price_nok=595,
                                          min_order_qty=20, events=["julebord"], allergens=["gluten", "mustard"],
                                          image_path="uploads/buffet.jpg"))


# ---- C1, menu by event --------------------------------------------------------------------------------
def test_p2_at01_published_dishes_are_shown_as_cards_with_everything_a_customer_needs(client, repos, soup):
    repos.food_items.add(make_item(name="Secret stew", published=False))
    html = page(client, "/")
    for text in ("Fish soup", "Creamy soup from Bergen", "189 NOK per person", "Minimum order: 10 portions",
                 "Contains: Fish, Milk", 'src="/static/uploads/soup.jpg"', 'alt="Fish soup"'):
        assert text in html, text
    assert "Secret stew" not in html


def test_p2_at02_a_dish_appears_in_every_event_it_is_offered_for_in_event_order(client, repos):
    repos.food_items.add(make_item(name="Salmon", events=["birthday", "wedding"]))
    repos.food_items.add(make_item(name="Sandwiches", events=["corporate_lunch"]))
    found = sections(page(client, "/"))
    assert list(found) == ["corporate_lunch", "wedding", "birthday"]        # the order of EVENTS; no empty ones
    assert "Salmon" in found["wedding"] and "Salmon" in found["birthday"]
    assert "Salmon" not in found["corporate_lunch"]


def test_p2_at03_choosing_an_event_shows_only_its_dishes(client, repos):
    repos.food_items.add(make_item(name="Wedding dinner", events=["wedding"]))
    repos.food_items.add(make_item(name="Sandwiches", events=["corporate_lunch"]))
    html = page(client, "/?event=wedding")
    assert list(sections(html)) == ["wedding"]
    assert "Wedding dinner" in html and "Sandwiches" not in html


def test_p2_at04_the_dietary_label_filter_alone_and_with_an_event(client, repos):
    repos.food_items.add(make_item(name="Beetroot salad", labels=["gluten_free"], allergens=["milk"],
                                   events=["conference", "birthday"]))
    repos.food_items.add(make_item(name="Lamb", events=["conference", "birthday"], allergens=["gluten"]))
    html = page(client, "/?label=gluten_free")
    assert "Beetroot salad" in html and "Lamb" not in html
    both = page(client, "/?event=birthday&label=gluten_free")
    assert list(sections(both)) == ["birthday"] and "Beetroot salad" in both and "Lamb" not in both


@pytest.mark.parametrize("query", ["event=funeral", "label=glutenfree", "event=wedding&label=keto"])
def test_p2_at05_an_unknown_filter_is_not_found_instead_of_an_unfiltered_menu(client, soup, query):
    assert client.get(f"/?{query}").status_code == 404


def test_p2_at06_a_dish_without_allergens_says_so(client, repos):
    repos.food_items.add(make_item(name="Fruit platter", allergens=[], no_allergens=True))
    assert "Contains none of the 14 allergens" in page(client, "/")


# ---- C2, shopping cart --------------------------------------------------------------------------------
def test_p2_at07_a_visitor_can_put_a_dish_in_the_cart_without_logging_in(client, soup):
    add(client, soup, 10)
    html = page(client, "/cart")
    assert "Fish soup" in html and 'value="10"' in html and "189 NOK" in html
    assert f"1{NBSP}890 NOK" in html                                          # 10 x 189
    assert "Cart (1)" in html


@pytest.mark.parametrize("portions", ["9", "0", "-10", "10.5", "ten", "", "1001"])
def test_p2_at08_a_wrong_number_is_refused_and_the_cart_is_unchanged(client, soup, portions):
    html = add(client, soup, portions).get_data(as_text=True)
    assert cart_of(client) == {}
    if portions in ("9", "0"):
        assert "The minimum order for “Fish soup” is 10 portions." in html
    add(client, soup, 10)
    client.post("/cart/update", data={"item_id": str(soup.id), "portions": portions})
    assert cart_of(client) == {str(soup.id): 10}


def test_p2_at09_adding_a_dish_again_adds_to_its_line(client, soup):
    add(client, soup, 10)
    add(client, soup, 5)
    assert cart_of(client) == {str(soup.id): 15}
    assert page(client, "/cart").count('name="item_id"') == 2               # one line: an update and a remove form


def test_p2_at10_a_line_can_be_changed_and_removed(client, soup, buffet):
    add(client, soup, 10)
    add(client, buffet, 20)
    client.post("/cart/update", data={"item_id": str(soup.id), "portions": "20"})
    html = page(client, "/cart")
    assert f"3{NBSP}780 NOK" in html                                          # 20 x 189
    assert f"15{NBSP}680 NOK" in html                                         # 3 780 + 20 x 595
    client.post("/cart/remove", data={"item_id": str(soup.id)})
    html = page(client, "/cart")                       # (the name is still in the "Removed ..." message)
    assert f'name="item_id" value="{soup.id}"' not in html and f"11{NBSP}900 NOK" in html
    assert cart_of(client) == {str(buffet.id): 20}


def test_p2_at11_the_estimated_total_is_the_sum_of_portions_times_price(client, soup, buffet):
    add(client, soup, 10)
    add(client, buffet, 20)
    html = page(client, "/cart")
    assert "Estimated total" in html and f"13{NBSP}790 NOK" in html           # 1 890 + 11 900
    assert "Ekte Mat confirms the final price" in html


def test_p2_at12_a_dish_taken_off_the_menu_leaves_the_cart_with_a_message(client, repos, soup, buffet):
    add(client, soup, 10)
    add(client, buffet, 20)
    soup.published = False
    repos.food_items.update(soup)
    repos.food_items.delete(buffet.id)
    html = page(client, "/cart")
    assert "“Fish soup” is no longer on the menu and was removed from your cart." in html
    assert "A dish in your cart is no longer on the menu and was removed." in html
    assert cart_of(client) == {} and "Your cart is empty." in html and "Cart (0)" in html


def test_p2_at13_the_cart_shows_todays_price_and_a_raised_minimum(client, repos, soup):
    add(client, soup, 10)
    soup.price_nok, soup.min_order_qty = 199, 20
    repos.food_items.update(soup)
    html = page(client, "/cart")
    assert f"1{NBSP}990 NOK" in html                                          # 10 x the new price
    assert "Below the minimum of 20 portions" in html
    assert cart_of(client) == {str(soup.id): 10}                               # the customer's number is kept


@pytest.mark.parametrize("item_id", ["hidden", "9999", "abc", ""])
def test_p2_at14_a_tampered_dish_id_adds_nothing(client, repos, item_id):
    hidden = repos.food_items.add(make_item(name="Secret stew", published=False))
    client.post("/cart/add", data={"item_id": str(hidden.id) if item_id == "hidden" else item_id, "portions": "10"})
    assert cart_of(client) == {}


def test_p2_at15_logging_in_keeps_the_cart_and_logging_out_empties_it(client, users, soup):
    add(client, soup, 10)
    log_in(client, "kari@test.example")
    assert cart_of(client) == {str(soup.id): 10}
    client.post("/account/logout")
    assert cart_of(client) == {}


def test_p2_at16_cart_forms_need_the_csrf_token(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "csrf.db")})  # CSRF on
    app.extensions["repositories"].reset()
    item = app.extensions["repositories"].food_items.add(make_item())
    client = app.test_client()
    for url in ("/cart/add", "/cart/update", "/cart/remove"):
        assert client.post(url, data={"item_id": str(item.id), "portions": "10"}).status_code == 400, url
    assert cart_of(client) == {}
    client.get("/")
    with client.session_transaction() as session:
        token = session["_csrf"]
    client.post("/cart/add", data={"item_id": str(item.id), "portions": "10", "csrf_token": token})
    assert cart_of(client) == {str(item.id): 10}


# ---- dietary labels and allergens (P2-8) --------------------------------------------------------------
def test_p2_at17_staff_cannot_save_a_label_that_the_allergens_contradict(admin, repos):
    form = {"name": "Banana pudding", "description": "Banana with pudding", "price_nok": "80",
            "min_order_qty": "2", "events": ["birthday"], "allergens": ["eggs", "milk"], "labels": ["vegan"]}
    response = admin.post("/admin/items/new", data=form)
    assert response.status_code == 400
    assert "A vegan dish can't contain Eggs, Milk." in unescape(response.get_data(as_text=True))
    assert repos.food_items.list() == []
    assert admin.post("/admin/items/new", data={**form, "labels": ["vegetarian", "halal"]}).status_code == 302
