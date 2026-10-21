"""Domain classes for Ekte Mat Online. Plain data and rules: no Flask, no database code."""
from dataclasses import dataclass, field

# Kinds of event a food item can be offered for (assignment C1; event types in the lab domain model).
EVENTS = {
    "corporate_lunch": "Corporate lunch",
    "conference": "Conference",
    "julebord": "Christmas party (julebord)",
    "wedding": "Wedding",
    "confirmation": "Confirmation",
    "birthday": "Birthday",
}

# The 14 allergens that must be declared under EU Regulation 1169/2011 (applies in Norway through the EEA).
ALLERGENS = {
    "gluten": "Cereals containing gluten",
    "crustaceans": "Crustaceans",
    "eggs": "Eggs",
    "fish": "Fish",
    "peanuts": "Peanuts",
    "soybeans": "Soybeans",
    "milk": "Milk",
    "nuts": "Tree nuts",
    "celery": "Celery",
    "mustard": "Mustard",
    "sesame": "Sesame seeds",
    "sulphites": "Sulphur dioxide and sulphites",
    "lupin": "Lupin",
    "molluscs": "Molluscs",
}

# Dietary labels: the kinds of dietary note found in Ekte Mat's 2024-2025 orders (lab, Task 4).
DIETARY_LABELS = {
    "vegetarian": "Vegetarian",
    "vegan": "Vegan",
    "gluten_free": "Gluten-free",
    "lactose_free": "Lactose-free",
    "halal": "Halal",
}

ROLES = ("customer", "admin")


def normalise_email(email):
    """E-mail addresses are compared without case and surrounding spaces."""
    return email.strip().lower()


@dataclass
class User:
    email: str
    name: str
    role: str                                   # "customer" or "admin"
    password_hash: str = field(repr=False)
    id: int | None = None

    @property
    def is_admin(self):
        return self.role == "admin"


@dataclass
class FoodItem:
    name: str
    description: str
    price_nok: int                              # price per person, whole NOK
    min_order_qty: int                          # minimum number of portions in one order
    events: list[str] = field(default_factory=list)
    allergens: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)
    published: bool = False
    image_path: str | None = None               # relative to the static folder, e.g. "uploads/seed-1.png"
    id: int | None = None
