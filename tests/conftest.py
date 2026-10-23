import io
import secrets
from datetime import date, datetime, timedelta

import pytest
from PIL import Image
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.domain import FoodItem, Order, OrderLine, User


@pytest.fixture
def app(tmp_path):
    """A fresh application with its own empty database file for every test."""
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "test.db"),
                      "UPLOAD_FOLDER": str(tmp_path / "uploads"), "CSRF_ENABLED": False})
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


def picture(fmt="JPEG", size=(120, 80), colour="red", **save_options):
    """Bytes of a small, real picture for upload tests."""
    buffer = io.BytesIO()
    Image.new("RGB" if fmt != "PNG" else "RGBA", size, colour).save(buffer, fmt, **save_options)
    return buffer.getvalue()


@pytest.fixture
def admin(client, users):
    """A test client logged in as the admin."""
    log_in(client, "admin@test.example")
    return client


def make_order(repos, customer_id, item_id, **changes):
    """Store an order straight through the repository (plan 4 tests); 10 portions at 189 NOK unless changed."""
    values = dict(customer_id=customer_id, event_type="conference", event_date=date.today() + timedelta(days=30),
                  guest_count=40, delivery_street="Bryggen 1", delivery_postcode="5003", delivery_city="Bergen",
                  submission_key=secrets.token_hex(16), submitted_at=datetime.now().replace(microsecond=0),
                  lines=[OrderLine(item_id, "", 10, 189)])
    values.update(changes)
    return repos.orders.add(Order(**values))
