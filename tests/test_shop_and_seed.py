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
