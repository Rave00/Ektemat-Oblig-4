from app.models.domain import STATUS_NAMES, order_from_form
from conftest import make_item
from seed import ADMIN, CUSTOMERS, FOOD, seed


def test_front_page_shows_only_published_items(client, repos):
    repos.food_items.add(make_item(name="Published soup", published=True))
    repos.food_items.add(make_item(name="Hidden soup", published=False))
    page = client.get("/").data
    assert b"Published soup" in page
    assert b"Hidden soup" not in page


def test_seed_creates_food_items_an_admin_and_customers(app, repos, tmp_path):
    seed(app, uploads=tmp_path / "uploads")
    items = repos.food_items.list()
    assert len(items) == len(FOOD)
    assert any(not item.published for item in items), "seed should include an unpublished item"
    assert all((tmp_path / item.image_path).exists() for item in items)     # image_path = "uploads/seed-N.png"
    assert repos.users.get_by_email(ADMIN[0]).is_admin
    assert all(repos.users.get_by_email(email).role == "customer" for email, _, _ in CUSTOMERS)


def test_seed_can_run_twice(app, repos, tmp_path):
    seed(app, uploads=tmp_path / "uploads")
    seed(app, uploads=tmp_path / "uploads")
    assert len(repos.food_items.list()) == len(FOOD)


def test_p4_at17_the_seed_has_sample_orders_in_every_status_that_pass_the_rules(app, repos, tmp_path):
    seed(app, uploads=tmp_path / "uploads")
    orders = repos.orders.list()
    assert {o.status for o in orders} == set(STATUS_NAMES)
    dishes = {item.id: item for item in repos.food_items.list()}
    for order in orders:
        form = {"event_type": order.event_type, "event_date": str(order.event_date), "guest_count": str(order.guest_count),
                "delivery_street": order.delivery_street, "delivery_postcode": order.delivery_postcode,
                "delivery_city": order.delivery_city}
        for n, group in enumerate(order.groups, 1):
            form.update({f"group_description_{n}": group.description, f"group_size_{n}": str(group.size),
                         f"group_allergies_{n}": group.allergy_notes, f"group_diet_{n}": group.diet_notes})
        sent = order.submitted_at.date()                      # V9 is checked against the day the order was sent
        _, errors = order_from_form(form, sent, [dishes[line.food_item_id] for line in order.lines])
        assert errors == {}, (order.number, errors)
        assert all(line.unit_price_nok == dishes[line.food_item_id].price_nok for line in order.lines)
        assert all(line.quantity >= dishes[line.food_item_id].min_order_qty for line in order.lines)
        assert (order.first_replied_at is None) == (order.status == "submitted")


def test_p5_at15_the_seed_has_answered_and_waiting_questions(app, repos, tmp_path):
    seed(app, uploads=tmp_path / "uploads")
    orders = repos.orders.list()
    questions = [q for order in orders for q in order.questions]
    assert any(q.answer for q in questions) and any(not q.answer for q in questions)
    for order in orders:
        for question in order.questions:
            assert question.customer_id == order.customer_id
            assert question.asked_at >= order.submitted_at
            assert not question.answer or question.answered_at >= question.asked_at
