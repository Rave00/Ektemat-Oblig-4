"""Domain classes for Ekte Mat Online. Plain data and rules: no Flask, no database code."""
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

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


# ---- accounts (plan 3, P3-1) ------------------------------------------------------------------------------
MIN_PASSWORD, MAX_PASSWORD = 10, 200          # ASSUMPTION: 10 characters; no source in the data pack
_EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")   # one @, and a dot somewhere after it


def validate_registration(name, email, password, password_again):
    """{field: message} for every rule a new account breaks; an empty dict means it can be created."""
    errors = {}
    if not name.strip():
        errors["name"] = "Enter your name."
    elif len(name.strip()) > 100:
        errors["name"] = "At most 100 characters."
    if len(email.strip()) > 254 or not _EMAIL.fullmatch(email.strip()):
        errors["email"] = "Enter an e-mail address such as kari@example.com."
    if len(password) < MIN_PASSWORD:
        errors["password"] = f"Use at least {MIN_PASSWORD} characters."
    elif len(password) > MAX_PASSWORD:
        errors["password"] = f"At most {MAX_PASSWORD} characters."
    if password != password_again:
        errors["password_again"] = "The two passwords are not the same."
    return errors


# ---- orders (plan 3) -----------------------------------------------------------------------------------------
STATUS_NAMES = {"submitted": "Submitted", "approved": "Approved", "in_preparation": "In preparation",
                "delivered": "Delivered", "rejected": "Rejected", "cancelled": "Cancelled"}       # plan 0, D10
PAYMENT_NAMES = {"not_paid": "Not paid", "deposit_paid": "Deposit paid", "invoiced": "Invoiced", "paid": "Paid"}

MAX_GUESTS = 400                 # V6: the event coordinator's daily capacity; lab report on the order data
MAX_DAYS_AHEAD = 730             # ASSUMPTION: two years, to catch typing mistakes such as 2062 (P3-3)
GROUP_ROWS = 5                   # guest group rows on the form (P3-4)
ORDER_LIMITS = {"delivery_street": 100, "delivery_city": 60, "group_description": 100, "group_notes": 300}


@dataclass
class GuestGroup:
    """Guests with the same allergies or dietary needs. No names: health data stays per group (US-40)."""
    description: str
    size: int
    allergy_notes: str = ""
    diet_notes: str = ""
    id: int | None = None


@dataclass
class OrderLine:
    food_item_id: int
    name: str                                   # the dish's name, filled in when the order is loaded
    quantity: int                               # portions
    unit_price_nok: int                         # price per person when the order was submitted (V7)
    id: int | None = None

    @property
    def total_nok(self):
        return self.quantity * self.unit_price_nok


@dataclass
class Order:
    customer_id: int | None
    event_type: str
    event_date: date | None
    guest_count: int
    delivery_street: str
    delivery_postcode: str
    delivery_city: str
    submission_key: str = ""                    # one order per click (P3-7)
    lines: list[OrderLine] = field(default_factory=list)
    groups: list[GuestGroup] = field(default_factory=list)
    status: str = "submitted"
    payment_status: str = "not_paid"
    submitted_at: datetime | None = None
    id: int | None = None

    @property
    def total_nok(self):
        """Always the sum of the lines; there is no stored total (V8)."""
        return sum(line.total_nok for line in self.lines)

    @property
    def number(self):
        return order_number(self.id, self.submitted_at)


def order_number(order_id, submitted_at):
    """'26-0007': the year it was submitted and the id, like the old order export (P3-8)."""
    return f"{submitted_at.year % 100:02d}-{order_id:04d}"


def _whole_number(text):
    text = str(text).strip()
    return int(text) if re.fullmatch(r"[0-9]{1,7}", text) else None


def _date(text):
    try:
        return date.fromisoformat(str(text).strip())
    except ValueError:
        return None


def order_from_form(form, today, dishes):
    """The order the customer typed (without lines) and {field: message} for every rule it breaks.

    `form` is any mapping of text values (the submitted form), `today` the current date (P3-11) and `dishes` the
    food items in the cart. Rules: P3-3 to P3-5 and V4, V5, V6, V9, V10 from the lab's order data report.
    """
    value = lambda name: str(form.get(name, "")).strip()
    errors = {}

    event_type = value("event_type")
    if event_type not in EVENTS:
        errors["event_type"] = "Choose the kind of event."
    else:
        not_offered = [dish.name for dish in dishes if event_type not in dish.events]
        if not_offered:
            verb = "is" if len(not_offered) == 1 else "are"
            errors["event_type"] = f"{', '.join(not_offered)} {verb} not offered for {EVENTS[event_type]}."

    event_date = _date(value("event_date"))
    if event_date is None:
        errors["event_date"] = "Enter the event date."
    elif event_date < today:
        errors["event_date"] = "The event date cannot be in the past."
    elif event_date > today + timedelta(days=MAX_DAYS_AHEAD):
        errors["event_date"] = "The event date can be at most two years ahead."

    guest_count = _whole_number(value("guest_count"))
    if guest_count is None or not 1 <= guest_count <= MAX_GUESTS:
        errors["guest_count"] = f"Enter a number of guests between 1 and {MAX_GUESTS}."

    for name, label in (("delivery_street", "the street address"), ("delivery_city", "the place")):
        if not value(name):
            errors[name] = f"Enter {label}."
        elif len(value(name)) > ORDER_LIMITS[name]:
            errors[name] = f"At most {ORDER_LIMITS[name]} characters."
    if not re.fullmatch(r"[0-9]{4}", value("delivery_postcode")):
        errors["delivery_postcode"] = "A postcode has four digits, for example 5003."

    groups = []
    for n in range(1, GROUP_ROWS + 1):
        description, size_text = value(f"group_description_{n}"), value(f"group_size_{n}")
        allergies, diet = value(f"group_allergies_{n}"), value(f"group_diet_{n}")
        if not any((description, size_text, allergies, diet)):
            continue                                                     # an empty row is ignored
        size = _whole_number(size_text)
        if not description or size is None or size < 1:
            errors[f"group_{n}"] = "Each group needs a description and a number of guests (at least 1)."
        elif len(description) > ORDER_LIMITS["group_description"]:
            errors[f"group_{n}"] = f"The description can be at most {ORDER_LIMITS['group_description']} characters."
        elif max(len(allergies), len(diet)) > ORDER_LIMITS["group_notes"]:
            errors[f"group_{n}"] = f"Allergies and dietary needs can be at most {ORDER_LIMITS['group_notes']} characters each."
        else:
            groups.append(GuestGroup(description, size, allergies, diet))
    in_groups = sum(group.size for group in groups)
    if guest_count and in_groups > guest_count and not any(key.startswith("group_") for key in errors):
        errors["groups"] = f"The guest groups have {in_groups} guests, but the order is for {guest_count}."

    order = Order(customer_id=None, event_type=event_type, event_date=event_date, guest_count=guest_count or 0,
                  delivery_street=value("delivery_street"), delivery_postcode=value("delivery_postcode"),
                  delivery_city=value("delivery_city"), groups=groups)
    return order, errors
