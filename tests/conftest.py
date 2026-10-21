import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.domain import FoodItem, User


@pytest.fixture
def app(tmp_path):
    """A fresh application with its own empty database file for every test."""
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "test.db"), "CSRF_ENABLED": False})
    app.extensions["repositories"].reset()
    return app


@pytest.fixture
def repos(app):
    return app.extensions["repositories"]


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def users(repos):
    """One admin and one customer; both use the password 'secret-pw'."""
    hashed = generate_password_hash("secret-pw")
    admin = repos.users.add(User(email="admin@test.example", name="Admin", role="admin", password_hash=hashed))
    customer = repos.users.add(User(email="kari@test.example", name="Kari", role="customer", password_hash=hashed))
    return {"admin": admin, "customer": customer}


def log_in(client, email, password="secret-pw"):
    return client.post("/account/login", data={"email": email, "password": password})


def make_item(**changes):
    values = dict(name="Fish soup", description="Soup", price_nok=189, min_order_qty=10,
                  events=["conference"], allergens=["fish", "milk"], labels=[], published=True)
    values.update(changes)
    return FoodItem(**values)
