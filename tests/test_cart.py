"""Cart rules of plan 2 (P2-1 to P2-4), tested without Flask or a database."""
import pytest

from app.models.cart import MAX_PORTIONS, Cart, CartError, estimated_total_nok, parse_portions
from conftest import make_item


def dish(item_id=1, **changes):
    item = make_item(**changes)            # Fish soup, 189 NOK per person, minimum 10, published
    item.id = item_id
    return item


# ---- the number the customer types ----------------------------------------------------------------
@pytest.mark.parametrize("text, portions", [("10", 10), (" 12 ", 12), ("0", 0), ("1000", 1000)])
def test_whole_numbers_are_read(text, portions):
    assert parse_portions(text) == portions


@pytest.mark.parametrize("text", ["", "  ", "ten", "-5", "2.5", "1e3", "10 portions", "9" * 5000],
                         ids=["empty", "spaces", "word", "negative", "decimal", "exponent", "with-text", "5000-digits"])
def test_anything_else_is_refused(text):
    with pytest.raises(CartError, match="whole number"):
        parse_portions(text)


# ---- adding ----------------------------------------------------------------------------------------
def test_a_dish_can_be_added_with_its_minimum_order():
    cart = Cart()
    cart.add(dish(), 10)
    assert cart.portions == {1: 10}


def test_below_the_minimum_is_refused_and_the_message_names_it():
    cart = Cart()
    with pytest.raises(CartError, match="The minimum order for “Fish soup” is 10 portions."):
        cart.add(dish(), 9)
    assert cart.portions == {}


def test_the_upper_limit_is_allowed_but_not_more():
    cart = Cart()
    cart.add(dish(), MAX_PORTIONS)
    with pytest.raises(CartError, match="At most 1 000 portions"):
        Cart().add(dish(), MAX_PORTIONS + 1)
    assert cart.portions == {1: 1000}


def test_adding_the_same_dish_again_adds_to_its_line():
    cart = Cart()
    cart.add(dish(), 10)
    cart.add(dish(), 5)                      # 5 alone is below the minimum, but the line becomes 15
    assert cart.portions == {1: 15}


def test_the_sum_is_checked_against_the_upper_limit():
    cart = Cart({1: 995})
    with pytest.raises(CartError):
        cart.add(dish(), 10)
    assert cart.portions == {1: 995}


@pytest.mark.parametrize("item", [None, dish(published=False)], ids=["missing", "unpublished"])
def test_only_dishes_on_the_menu_can_be_added(item):
    cart = Cart()
    with pytest.raises(CartError, match="not on the menu"):
        cart.add(item, 10)
    assert cart.portions == {}


# ---- changing and removing -------------------------------------------------------------------------
def test_the_number_of_portions_can_be_changed():
    cart = Cart({1: 10})
    cart.set_quantity(dish(), 25)
    assert cart.portions == {1: 25}


@pytest.mark.parametrize("portions", [0, 9, 1001])
def test_a_change_below_the_minimum_or_above_the_limit_is_refused(portions):
    cart = Cart({1: 10})
    with pytest.raises(CartError):
        cart.set_quantity(dish(), portions)
    assert cart.portions == {1: 10}


def test_a_dish_that_is_not_in_the_cart_cannot_be_changed():
    with pytest.raises(CartError, match="not in your cart"):
        Cart().set_quantity(dish(), 10)


def test_a_line_can_be_removed():
    cart = Cart({1: 10, 2: 20})
    cart.remove(1)
    cart.remove(99)                          # removing something that is not there is harmless
    assert cart.portions == {2: 20}


# ---- lines, current prices and the estimated total -------------------------------------------------
def test_lines_use_todays_dishes_and_prices():
    cart = Cart({1: 10, 2: 20})
    lines, removed = cart.lines({1: dish(1), 2: dish(2, name="Buffet", price_nok=595, min_order_qty=20)})
    assert [(line.item.name, line.portions, line.total_nok) for line in lines] == [
        ("Buffet", 20, 11900), ("Fish soup", 10, 1890)]                        # sorted by name
    assert removed == []
    assert estimated_total_nok(lines) == 13790


def test_lines_are_sorted_by_name_whatever_the_order_in_the_session():
    cart = Cart({10: 10, 5: 10, 1: 10})
    lines, _ = cart.lines({1: dish(1, name="fish soup"), 5: dish(5, name="Traditional buffet"),
                           10: dish(10, name="Meeting sandwiches")})
    assert [line.item.name for line in lines] == ["fish soup", "Meeting sandwiches", "Traditional buffet"]


def test_dishes_no_longer_for_sale_are_taken_out_of_the_cart():
    cart = Cart({1: 10, 2: 10, 3: 10})
    lines, removed = cart.lines({1: dish(1), 2: dish(2, name="Old soup", published=False)})   # 3 was deleted
    assert [line.item.id for line in lines] == [1]
    assert removed == ["Old soup", None]
    assert cart.portions == {1: 10}


def test_a_raised_minimum_marks_the_line_but_keeps_the_customers_number():
    cart = Cart({1: 10})
    [line], _ = cart.lines({1: dish(1, min_order_qty=20)})
    assert line.below_minimum and line.portions == 10


def test_an_empty_cart_has_a_total_of_zero():
    assert estimated_total_nok([]) == 0


# ---- the session ------------------------------------------------------------------------------------
def test_the_cart_is_stored_as_text_keys_and_read_back():
    cart = Cart({1: 10})
    assert cart.to_session() == {"1": 10}
    assert Cart.from_session({"1": 10}).portions == {1: 10}


def test_unreadable_session_values_are_ignored():
    assert Cart.from_session({"1": 10, "x": 5, "2": "many", "3": -4}).portions == {1: 10}
    assert Cart.from_session(None).portions == {} and Cart.from_session("junk").portions == {}
