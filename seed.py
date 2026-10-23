"""Fill the database with synthetic sample data: food items (with placeholder pictures), one admin, test customers
and sample orders.

Run:  python seed.py
WARNING: deletes all existing data first. Synthetic data only; the passwords are for local development.

Dishes and prices come from the lab data pack (autumn lunch menu and the menu packages in the order export).
Minimum order quantities, events and allergens are ASSUMPTIONS for demonstration. The sample orders are invented;
their dates are counted from the day the seed runs (plan 4, P4-9).
"""
import secrets
from datetime import date, datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.domain import FoodItem, GuestGroup, Order, OrderLine, User

ADMIN = ("admin@ektemat.example", "Ekte Mat admin", "admin-dev-1")
CUSTOMERS = [("kunde1@example.com", "Test Customer One", "customer-dev-1"),
             ("kunde2@example.com", "Test Customer Two", "customer-dev-2")]

# (name, description, price NOK per person, minimum order, events, allergens, dietary labels, published, colour)
FOOD = [
    ("Fish soup with Bergen cod", "Creamy fish soup with root vegetables, served with sourdough bread.",
     189, 10, ["corporate_lunch", "conference"], ["fish", "milk", "gluten", "celery"], [], True, "#3d6f8e"),
    ("Slow-cooked lamb from Voss", "Lamb from a farm in Voss with barley risotto and seasonal greens.",
     245, 10, ["corporate_lunch", "conference", "birthday"], ["gluten", "milk", "celery"], [], True, "#7a4a33"),
    ("Beetroot and chickpea salad", "Roasted beetroot, chickpeas and goat cheese from Hardanger.",
     165, 10, ["corporate_lunch", "conference", "birthday", "confirmation"], ["milk", "mustard"],
     ["vegetarian", "gluten_free"], True, "#8e3d5a"),
    ("Rakfisk tasting", "Traditional fermented trout with flatbread and sour cream. November only.",
     210, 10, ["julebord"], ["fish", "milk", "gluten"], [], False, "#5d6b70"),
    ("Traditional julebord buffet", "Pork ribs, pinnekjøtt, medisterkaker, sauerkraut and red cabbage.",
     595, 20, ["julebord"], ["gluten", "milk", "mustard", "celery", "sulphites"], [], True, "#8e2f2f"),
    ("Seasonal lunch buffet", "Bread, spreads, salads and a warm dish of the week.",
     229, 10, ["corporate_lunch", "conference"], ["gluten", "milk", "eggs"], [], True, "#6b7d3a"),
    ("Vegetarian harvest menu", "Root vegetable gratin, lentil salad and baked autumn apples.",
     245, 10, ["corporate_lunch", "conference", "birthday", "confirmation"], ["milk", "gluten", "nuts"],
     ["vegetarian"], True, "#a0702a"),
    ("Fish and seafood menu", "Smoked salmon, prawns, mussels and baked cod with butter sauce.",
     495, 15, ["wedding", "birthday", "conference"], ["fish", "crustaceans", "molluscs", "milk"], [], True,
     "#2f5d7a"),
    ("Wedding served dinner, three courses", "Starter, main course and dessert, served at the table.",
     875, 30, ["wedding"], ["gluten", "milk", "eggs", "fish", "celery"], [], True, "#5a4a7a"),
    ("Meeting sandwiches", "Open sandwiches on sourdough with seasonal toppings.",
     129, 8, ["corporate_lunch", "conference"], ["gluten", "milk", "eggs", "mustard"], [], True, "#3a7d6b"),
    ("Confirmation buffet", "Roast beef, salmon, potato salad, bread and cake for the confirmation.",
     395, 20, ["confirmation", "birthday"], ["gluten", "milk", "eggs", "fish"], [], True, "#2f5d46"),
]

# Sample orders, one per status (plan 4, P4-9). Synthetic: no real customers, no names in the guest groups.
# (customer, status, payment, sent: hours ago, first reply: hours after sending, event: days from today,
#  event type, guests, address, [(dish, portions)], [(group, size, allergies, diet)], reason)
ORDERS = [
    (0, "submitted", "not_paid", 30, None, 14, "corporate_lunch", 20, ("Strandkaien 8", "5013", "Bergen"),
     [("Fish soup with Bergen cod", 20), ("Meeting sandwiches", 20)], [("Gluten-free", 2, "Gluten (coeliac)", "")], ""),
    (1, "submitted", "not_paid", 1, None, 21, "birthday", 15, ("Fjellveien 12", "5019", "Bergen"),
     [("Slow-cooked lamb from Voss", 15)], [("Children", 4, "", "Mild food, no spices")], ""),
    (0, "approved", "deposit_paid", 120, 5, 45, "wedding", 60, ("Solstrand 1", "5200", "Os"),
     [("Wedding served dinner, three courses", 60), ("Fish and seafood menu", 15)],
     [("Nut allergy", 3, "Tree nuts and peanuts", ""), ("Vegetarians", 8, "", "Vegetarian")], ""),
    (1, "in_preparation", "invoiced", 240, 20, 2, "conference", 40, ("Lars Hilles gate 3", "5008", "Bergen"),
     [("Seasonal lunch buffet", 40)], [("Lactose intolerance", 5, "", "Lactose-free")], ""),
    (1, "delivered", "paid", 600, 3, -3, "corporate_lunch", 12, ("Kong Oscars gate 20", "5017", "Bergen"),
     [("Beetroot and chickpea salad", 12)], [], ""),
    (0, "rejected", "not_paid", 72, 26, 10, "julebord", 25, ("Nordnesveien 5", "5005", "Bergen"),
     [("Traditional julebord buffet", 25)], [], "We are fully booked for julebord on this date."),
    (1, "cancelled", "not_paid", 96, 2, 40, "confirmation", 30, ("Kalfarveien 31", "5018", "Bergen"),
     [("Confirmation buffet", 30)], [("Egg allergy", 1, "Eggs", "")], "Cancelled by phone at the customer's request."),
]


def sample_orders(repos, customers, dishes, now=None):
    now = now or datetime.now().replace(microsecond=0)
    for who, status, payment, sent_ago, replied_after, days, event, guests, address, lines, groups, reason in ORDERS:
        sent = now - timedelta(hours=sent_ago)
        repos.orders.add(Order(
            customer_id=customers[who].id, event_type=event, event_date=date.today() + timedelta(days=days),
            guest_count=guests, delivery_street=address[0], delivery_postcode=address[1], delivery_city=address[2],
            submission_key=secrets.token_hex(16), submitted_at=sent, status=status, payment_status=payment,
            status_reason=reason, first_replied_at=sent + timedelta(hours=replied_after) if replied_after else None,
            lines=[OrderLine(dishes[name].id, name, portions, dishes[name].price_nok) for name, portions in lines],
            groups=[GuestGroup(*group) for group in groups]))


def placeholder_image(folder, number, name, colour):
    """Draw a simple picture with the dish name, so the menu has images without any image files in Git."""
    image = Image.new("RGB", (600, 400), colour)
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 270, 600, 400], fill=_darker(colour))        # darker band behind the name
    font = ImageFont.load_default(size=34)
    lines, line = [], ""
    for word in name.split():
        trial = f"{line} {word}".strip()
        if draw.textlength(trial, font=font) > 540 and line:
            lines.append(line)
            line = word
        else:
            line = trial
    lines.append(line)
    for i, text in enumerate(lines[:2]):
        draw.text((30, 290 + i * 44), text, font=font, fill="#ffffff")
    path = folder / f"seed-{number}.png"
    image.save(path)
    return f"uploads/{path.name}"


def _darker(colour, factor=0.7):
    r, g, b = (int(colour[i:i + 2], 16) for i in (1, 3, 5))
    return f"#{int(r * factor):02x}{int(g * factor):02x}{int(b * factor):02x}"


def seed(app, uploads=None):
    repos = app.extensions["repositories"]
    repos.reset()
    uploads = Path(uploads or app.config["UPLOAD_FOLDER"])
    uploads.mkdir(parents=True, exist_ok=True)
    # The database is empty again, so no stored picture is in use any more: remove them all.
    for old in [*uploads.glob("*.png"), *uploads.glob("*.jpg"), *uploads.glob("pending/*.jpg")]:
        old.unlink()

    email, name, password = ADMIN
    repos.users.add(User(email=email, name=name, role="admin", password_hash=generate_password_hash(password)))
    customers = [repos.users.add(User(email=email, name=name, role="customer",
                                      password_hash=generate_password_hash(password)))
                 for email, name, password in CUSTOMERS]
    dishes = {}
    for number, (name, description, price, minimum, events, allergens, labels, published, colour) in enumerate(FOOD, 1):
        dishes[name] = repos.food_items.add(FoodItem(
            name=name, description=description, price_nok=price, min_order_qty=minimum,
            events=events, allergens=allergens, labels=labels, published=published,
            image_path=placeholder_image(uploads, number, name, colour)))
    sample_orders(repos, customers, dishes)


if __name__ == "__main__":
    app = create_app()
    seed(app)
    print(f"Seeded {len(FOOD)} food items, {len(ORDERS)} sample orders, 1 admin and {len(CUSTOMERS)} test customers"
          f" into {app.config['DATABASE']}")
    print("Log in (development only):")
    for email, _, password in [ADMIN, *CUSTOMERS]:
        print(f"  {email:28} {password}")
