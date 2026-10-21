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

# Allergens that prove a dietary label wrong (plan 2, P2-8). ASSUMPTION from common food knowledge, not from the
# data pack. Lactose-free milk still contains milk protein, and halal cannot be judged from allergens, so those
# two labels have no rule.
LABEL_EXCLUDES = {
    "vegan": ("eggs", "milk", "fish", "crustaceans", "molluscs"),
    "vegetarian": ("fish", "crustaceans", "molluscs"),
    "gluten_free": ("gluten",),
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
    no_allergens: bool = False                  # ticked: "contains none of the 14 allergens" (plan 1, P1-2)
    published: bool = False
    image_path: str | None = None               # relative to the static folder, e.g. "uploads/seed-1.png"
    id: int | None = None


# ---- rules for food items (plan 1, P1-1 to P1-3) ------------------------------------------------------
LIMITS = {"name": 100, "description": 500, "price_nok": 100_000, "min_order_qty": 1000}

ALLERGEN_INFO_MISSING = "Allergen information missing"      # exact wording from lab backlog US-02
PICTURE_MISSING = "Picture missing"


def validate_food_item(item):
    """Return {field: message} for every rule the item breaks; an empty dict means the item is valid."""
    errors = {}
    if not item.name.strip():
        errors["name"] = "Enter a name."
    elif len(item.name) > LIMITS["name"]:
        errors["name"] = f"At most {LIMITS['name']} characters."
    if not item.description.strip():
        errors["description"] = "Enter a description."
    elif len(item.description) > LIMITS["description"]:
        errors["description"] = f"At most {LIMITS['description']} characters."
    if not 0 <= item.price_nok <= LIMITS["price_nok"]:
        errors["price_nok"] = "Enter a price between 0 and 100 000 NOK."
    if not 1 <= item.min_order_qty <= LIMITS["min_order_qty"]:
        errors["min_order_qty"] = f"Enter a number between 1 and {LIMITS['min_order_qty']}."
    if not item.events:
        errors["events"] = "Tick at least one event."
    for attr, known in (("events", EVENTS), ("allergens", ALLERGENS), ("labels", DIETARY_LABELS)):
        unknown = set(getattr(item, attr)) - known.keys()
        if unknown:
            errors[attr] = f"Unknown value: {', '.join(sorted(unknown))}."
    if item.allergens and item.no_allergens:
        errors["allergens"] = "Tick the allergens, or \"contains none of the 14 allergens\", not both."
    contradicted = label_conflicts(item)
    if contradicted and "labels" not in errors:
        errors["labels"] = " ".join(contradicted)
    return errors


def label_conflicts(item):
    """One message per dietary label that the item's allergens prove wrong (plan 2, P2-8)."""
    messages = []
    for label, excluded in LABEL_EXCLUDES.items():
        found = [name for code, name in ALLERGENS.items() if code in excluded and code in item.allergens]
        if label in item.labels and found:
            messages.append(f"A {DIETARY_LABELS[label].lower()} dish can't contain {', '.join(found)}.")
    return messages


def publish_problems(item):
    """Reasons why the item may not be shown on the customer menu; an empty list means it can be published."""
    problems = []
    if not item.allergens and not item.no_allergens:
        problems.append(ALLERGEN_INFO_MISSING)
    if not item.image_path:
        problems.append(PICTURE_MISSING)
    return problems


# ---- the customer menu (C1, plan 2, P2-5 and P2-6) -------------------------------------------------------
def menu_sections(items, event=None, label=None):
    """The menu as a list of (event code, event name, dishes), in the order of EVENTS.

    Only published dishes are included. A dish offered for several events is in each of those sections, and an
    event without dishes has no section. `event` keeps one section (US-01, criterion 2); `label` keeps only
    dishes with that dietary label (US-02, criterion 3). An unknown code raises ValueError, so a mistyped filter
    can never look like a filtered menu.
    """
    if event is not None and event not in EVENTS:
        raise ValueError(f"Unknown event: {event}")
    if label is not None and label not in DIETARY_LABELS:
        raise ValueError(f"Unknown dietary label: {label}")
    sections = []
    for code, name in EVENTS.items():
        if event is not None and code != event:
            continue
        dishes = [item for item in items
                  if item.published and code in item.events and (label is None or label in item.labels)]
        if dishes:
            sections.append((code, name, dishes))
    return sections
