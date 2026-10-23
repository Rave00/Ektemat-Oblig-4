"""Shopping cart rules (C2, plan 2, decisions P2-1 to P2-4).

The cart only knows dish ids and numbers of portions. Names and prices are read again from the repository
every time (P2-3), so the cart never shows an old price or a dish that is no longer for sale.
"""
import re
from dataclasses import dataclass

from .domain import FoodItem, OrderLine

# Most portions of one dish in one cart. ASSUMPTION: far above the kitchen's stated capacity of about
# 400 covers a day (lab backlog C-16), so it only stops typing mistakes (P2-2).
MAX_PORTIONS = 1000

_WHOLE_NUMBER = re.compile(r"[0-9]{1,7}")      # 7 digits is plenty; very long text never reaches int()


class CartError(ValueError):
    """A change the cart refuses. The message is written for the customer."""


@dataclass
class CartLine:
    item: FoodItem
    portions: int

    @property
    def total_nok(self) -> int:
        return self.portions * self.item.price_nok

    @property
    def below_minimum(self) -> bool:
        """True when staff have raised the minimum order since the dish was put in the cart (P2-3)."""
        return self.portions < self.item.min_order_qty


def parse_portions(text) -> int:
    """The number the customer typed, as a whole number of portions."""
    text = str(text).strip()
    if not _WHOLE_NUMBER.fullmatch(text):
        raise CartError("Enter the number of portions as a whole number.")
    return int(text)


def estimated_total_nok(lines) -> int:
    """C2: the estimated total is the sum of portions x price per person (P2-4)."""
    return sum(line.total_nok for line in lines)


class Cart:
    def __init__(self, portions=None):
        self.portions: dict[int, int] = dict(portions or {})

    # ---- the session stores {"dish id": portions}; JSON keys are always text -----------------------
    @classmethod
    def from_session(cls, data):
        portions = {}
        if isinstance(data, dict):
            for key, value in data.items():
                if _WHOLE_NUMBER.fullmatch(str(key)) and isinstance(value, int) and value > 0:
                    portions[int(key)] = value
        return cls(portions)

    def to_session(self) -> dict[str, int]:
        return {str(item_id): portions for item_id, portions in self.portions.items()}

    # ---- changes ----------------------------------------------------------------------------------
    def add(self, item, portions):
        """Add portions of a dish; a dish already in the cart gets the sum (P2-2)."""
        _check_for_sale(item)
        total = self.portions.get(item.id, 0) + portions
        _check_portions(item, total)
        self.portions[item.id] = total

    def set_quantity(self, item, portions):
        if item is None or item.id not in self.portions:
            raise CartError("This dish is not in your cart.")
        _check_for_sale(item)
        _check_portions(item, portions)
        self.portions[item.id] = portions

    def remove(self, item_id):
        self.portions.pop(item_id, None)

    # ---- what the cart page shows -----------------------------------------------------------------
    def lines(self, items_by_id):
        """Today's lines, plus the names of the dishes taken out because they are no longer for sale.

        `items_by_id` holds every dish in the repository, published or not. A deleted dish is missing,
        so its name is unknown (None).
        """
        lines, removed = [], []
        for item_id, portions in list(self.portions.items()):
            item = items_by_id.get(item_id)
            if item is None or not item.published:
                removed.append(item.name if item else None)
                del self.portions[item_id]
            else:
                lines.append(CartLine(item, portions))
        # By name, like the menu: the session does not keep the order dishes were added in (Flask sorts its keys).
        return sorted(lines, key=lambda line: line.item.name.casefold()), removed


def _check_for_sale(item):
    if item is None or not item.published:
        raise CartError("This dish is not on the menu.")


def _check_portions(item, portions):
    if portions < item.min_order_qty:
        raise CartError(f"The minimum order for “{item.name}” is {item.min_order_qty} portions.")
    if portions > MAX_PORTIONS:
        raise CartError("At most 1 000 portions of one dish. For larger events, please contact Ekte Mat.")


def order_lines_from(lines):
    """Turn cart lines into order lines with today's price per person copied in (V7; plan 0, D8)."""
    return [OrderLine(line.item.id, line.item.name, line.portions, line.item.price_nok) for line in lines]
