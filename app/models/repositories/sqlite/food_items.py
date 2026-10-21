from ...domain import FoodItem
from ..base import FoodItemRepository

# The three lists of a food item are stored in link tables (one row per value).
LINKS = {"events": ("food_item_events", "event"),
         "allergens": ("food_item_allergens", "allergen"),
         "labels": ("food_item_labels", "label")}

SELECT = (
    "SELECT f.*, "
    + ", ".join(f"(SELECT group_concat({col}, ',') FROM {table} WHERE food_item_id = f.id) AS {attr}"
                for attr, (table, col) in LINKS.items())
    + " FROM food_items f"
)


def _to_item(row):
    if row is None:
        return None
    split = lambda value: sorted(value.split(",")) if value else []
    return FoodItem(id=row["id"], name=row["name"], description=row["description"],
                    price_nok=row["price_nok"], min_order_qty=row["min_order_qty"],
                    image_path=row["image_path"], published=bool(row["published"]),
                    events=split(row["events"]), allergens=split(row["allergens"]),
                    labels=split(row["labels"]))


class SqliteFoodItemRepository(FoodItemRepository):
    def __init__(self, db):
        self.db = db

    def list(self, published_only=False):
        where = " WHERE f.published = 1" if published_only else ""
        with self.db.connect() as conn:
            return [_to_item(r) for r in conn.execute(SELECT + where + " ORDER BY f.name")]

    def get(self, item_id):
        with self.db.connect() as conn:
            return _to_item(conn.execute(SELECT + " WHERE f.id = ?", (item_id,)).fetchone())

    def add(self, item):
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO food_items (name, description, price_nok, min_order_qty, image_path, published) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (item.name, item.description, item.price_nok, item.min_order_qty, item.image_path,
                 int(item.published)))
            self._save_links(conn, cur.lastrowid, item)
            return _to_item(conn.execute(SELECT + " WHERE f.id = ?", (cur.lastrowid,)).fetchone())

    def update(self, item):
        with self.db.connect() as conn:
            conn.execute(
                "UPDATE food_items SET name = ?, description = ?, price_nok = ?, min_order_qty = ?, "
                "image_path = ?, published = ? WHERE id = ?",
                (item.name, item.description, item.price_nok, item.min_order_qty, item.image_path,
                 int(item.published), item.id))
            self._save_links(conn, item.id, item)

    def delete(self, item_id):
        with self.db.connect() as conn:
            conn.execute("DELETE FROM food_items WHERE id = ?", (item_id,))

    @staticmethod
    def _save_links(conn, item_id, item):
        for attr, (table, col) in LINKS.items():
            conn.execute(f"DELETE FROM {table} WHERE food_item_id = ?", (item_id,))
            conn.executemany(f"INSERT INTO {table} (food_item_id, {col}) VALUES (?, ?)",
                             [(item_id, value) for value in sorted(set(getattr(item, attr)))])
