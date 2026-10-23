import sqlite3
from datetime import date, datetime

from ...domain import GuestGroup, Order, OrderLine
from ..base import OrderRepository


class SqliteOrderRepository(OrderRepository):
    def __init__(self, db):
        self.db = db

    def add(self, order):
        try:
            with self.db.connect() as conn:                 # one transaction: everything is stored, or nothing
                order_id = conn.execute(
                    "INSERT INTO orders (customer_id, event_type, event_date, guest_count, delivery_street,"
                    " delivery_postcode, delivery_city, status, payment_status, submitted_at, submission_key)"
                    " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (order.customer_id, order.event_type, order.event_date.isoformat(), order.guest_count,
                     order.delivery_street, order.delivery_postcode, order.delivery_city, order.status,
                     order.payment_status, order.submitted_at.isoformat(sep=" ", timespec="seconds"),
                     order.submission_key)).lastrowid
                conn.executemany(
                    "INSERT INTO order_lines (order_id, food_item_id, quantity, unit_price_nok) VALUES (?, ?, ?, ?)",
                    [(order_id, line.food_item_id, line.quantity, line.unit_price_nok) for line in order.lines])
                conn.executemany(
                    "INSERT INTO guest_groups (order_id, description, size, allergy_notes, diet_notes)"
                    " VALUES (?, ?, ?, ?, ?)",
                    [(order_id, g.description, g.size, g.allergy_notes, g.diet_notes) for g in order.groups])
        except sqlite3.IntegrityError as error:
            if "orders.submission_key" in str(error):       # the same form again (P3-7): return the first order
                return self.get_by_submission_key(order.submission_key)
            raise
        return self.get(order_id)

    def get(self, order_id):
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE id = ?", (order_id,)).fetchone()
            return self._load(conn, row)

    def get_by_submission_key(self, key):
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM orders WHERE submission_key = ?", (key,)).fetchone()
            return self._load(conn, row)

    @staticmethod
    def _load(conn, row):
        if row is None:
            return None
        lines = [OrderLine(id=r["id"], food_item_id=r["food_item_id"], name=r["name"], quantity=r["quantity"],
                           unit_price_nok=r["unit_price_nok"])
                 for r in conn.execute("SELECT l.*, f.name FROM order_lines l JOIN food_items f ON f.id = l.food_item_id"
                                       " WHERE l.order_id = ? ORDER BY l.id", (row["id"],))]
        groups = [GuestGroup(id=r["id"], description=r["description"], size=r["size"],
                             allergy_notes=r["allergy_notes"] or "", diet_notes=r["diet_notes"] or "")
                  for r in conn.execute("SELECT * FROM guest_groups WHERE order_id = ? ORDER BY id", (row["id"],))]
        return Order(id=row["id"], customer_id=row["customer_id"], event_type=row["event_type"],
                     event_date=date.fromisoformat(row["event_date"]), guest_count=row["guest_count"],
                     delivery_street=row["delivery_street"], delivery_postcode=row["delivery_postcode"],
                     delivery_city=row["delivery_city"], status=row["status"], payment_status=row["payment_status"],
                     submitted_at=datetime.fromisoformat(row["submitted_at"]), submission_key=row["submission_key"],
                     lines=lines, groups=groups)
