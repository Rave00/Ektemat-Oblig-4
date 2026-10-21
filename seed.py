"""Fill the database with synthetic sample data: food items (with placeholder pictures), one admin, test customers.

Run:  python seed.py
WARNING: deletes all existing data first. Synthetic data only; the passwords are for local development.

Dishes and prices come from the lab data pack (autumn lunch menu and the menu packages in the order export).
Minimum order quantities, events and allergens are ASSUMPTIONS for demonstration.
"""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.domain import FoodItem, User

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

UPLOADS = Path(__file__).parent / "app" / "views" / "static" / "uploads"


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


def seed(app, uploads=UPLOADS):
    repos = app.extensions["repositories"]
    repos.reset()
    uploads.mkdir(parents=True, exist_ok=True)
    for old in uploads.glob("seed-*.png"):
        old.unlink()

    email, name, password = ADMIN
    repos.users.add(User(email=email, name=name, role="admin", password_hash=generate_password_hash(password)))
    for email, name, password in CUSTOMERS:
        repos.users.add(User(email=email, name=name, role="customer",
                             password_hash=generate_password_hash(password)))
    for number, (name, description, price, minimum, events, allergens, labels, published, colour) in enumerate(FOOD, 1):
        repos.food_items.add(FoodItem(
            name=name, description=description, price_nok=price, min_order_qty=minimum,
            events=events, allergens=allergens, labels=labels, published=published,
            image_path=placeholder_image(uploads, number, name, colour)))


if __name__ == "__main__":
    app = create_app()
    seed(app)
    print(f"Seeded {len(FOOD)} food items, 1 admin and {len(CUSTOMERS)} test customers into {app.config['DATABASE']}")
    print("Log in (development only):")
    for email, _, password in [ADMIN, *CUSTOMERS]:
        print(f"  {email:28} {password}")
