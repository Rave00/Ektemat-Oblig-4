import sqlite3
from datetime import date, datetime

from ...domain import GuestGroup, Order, OrderLine
from ..base import OrderRepository

# Every order is loaded with its customer's name and e-mail address (for the staff pages, plan 4).
SELECT = ("SELECT o.*, u.name AS customer_name, u.email AS customer_email"
          " FROM orders o JOIN users u ON u.id = o.customer_id")


def _time(value):
    return value.isoformat(sep=" ", timespec="seconds") if value else None


class SqliteOrderRepository(OrderRepository):
    def __init__(self, db):
        self.db = db

    def add(self, order):
        try:
            with self.db.connect() as conn:                 # one transaction: everything is stored, or nothing
                order_id = conn.execute(
                    "INSERT INTO orders (customer_id, event_type, event_date, guest_count, delivery_street,"
                    " delivery_postcode, delivery_city, status, payment_status, submitted_at, submission_key,"
                    " status_reason, first_replied_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (order.customer_id, order.event_type, order.event_date.isoformat(), order.guest_count,
                     order.delivery_street, order.delivery_postcode, order.delivery_city, order.status,
                     order.payment_status, _time(order.submitted_at), order.submission_key,
                     order.status_reason or None, _time(order.first_replied_at))).lastrowid
                conn.executemany(
                    "INSERT INTO order_lines (order_id, food_item_id, quantity, unit_price_nok) VALUES (?, ?, ?, ?)",
                    [(order_id, line.food_item_id, line.quantity, line.unit_price_nok) for line in order.lines])
                conn.executemany(
                    "INSERT INTO guest_groups (order_id, description, size, allergy_notes, diet_notes)"
                    " VALUES (?, ?, ?, ?, ?)",
                    [(order_id, g.description, g.size, g.allergy_notes, g.diet_notes) for g in order.groups])
        except sqlite3.IntegrityError as error:
            if "orders.submission_key" in str(error):       # the same form again (plan 3, P3-7): the first order
                return self.get_by_submission_key(order.submission_key)
            raise
        return self.get(order_id)

    def get(self, order_id):
        with self.db.connect() as conn:
            return next(iter(self._load(conn, SELECT + " WHERE o.id = ?", (order_id,))), None)

    def get_by_submission_key(self, key):
        with self.db.connect() as conn:
            return next(iter(self._load(conn, SELECT + " WHERE o.submission_key = ?", (key,))), None)

    def list(self, status=None, date_from=None, date_to=None):
        conditions, values = [], []
        for condition, value in (("o.status = ?", status), ("o.event_date >= ?", date_from),
                                 ("o.event_date <= ?", date_to)):
            if value is not None:
                conditions.append(condition)
                values.append(value.isoformat() if isinstance(value, date) else value)
        where = " WHERE " + " AND ".join(conditions) if conditions else ""
        with self.db.connect() as conn:
            return self._load(conn, SELECT + where + " ORDER BY o.event_date, o.id", values)

    def list_for_customer(self, customer_id):
        with self.db.connect() as conn:
            return self._load(conn, SELECT + " WHERE o.customer_id = ? ORDER BY o.submitted_at DESC, o.id DESC",
                              (customer_id,))

    def update_status(self, order, expected_status):
        with self.db.connect() as conn:                     # "only if it is still ...": no lost or crossed changes
            changed = conn.execute(
                "UPDATE orders SET status = ?, status_reason = ?, first_replied_at = ? WHERE id = ? AND status = ?",
                (order.status, order.status_reason or None, _time(order.first_replied_at), order.id,
                 expected_status)).rowcount
        return changed == 1

    def update_payment_status(self, order_id, payment_status):
        with self.db.connect() as conn:
            conn.execute("UPDATE orders SET payment_status = ? WHERE id = ?", (payment_status, order_id))

    @staticmethod
    def _load(conn, query, values):
        """Orders from `query`, each with its lines (and the dishes' names) and guest groups: three queries in all."""
        rows = conn.execute(query, values).fetchall()
        ids = [row["id"] for row in rows]
        lines, groups = {i: [] for i in ids}, {i: [] for i in ids}
        if ids:
            marks = ", ".join("?" * len(ids))
            for r in conn.execute("SELECT l.*, f.name FROM order_lines l JOIN food_items f ON f.id = l.food_item_id"
                                  f" WHERE l.order_id IN ({marks}) ORDER BY l.id", ids):
                lines[r["order_id"]].append(OrderLine(id=r["id"], food_item_id=r["food_item_id"], name=r["name"],
                                                      quantity=r["quantity"], unit_price_nok=r["unit_price_nok"]))
            for r in conn.execute(f"SELECT * FROM guest_groups WHERE order_id IN ({marks}) ORDER BY id", ids):
                groups[r["order_id"]].append(GuestGroup(id=r["id"], description=r["description"], size=r["size"],
                                                        allergy_notes=r["allergy_notes"] or "",
                                                        diet_notes=r["diet_notes"] or ""))
        return [Order(id=row["id"], customer_id=row["customer_id"], event_type=row["event_type"],
                      event_date=date.fromisoformat(row["event_date"]), guest_count=row["guest_count"],
                      delivery_street=row["delivery_street"], delivery_postcode=row["delivery_postcode"],
                      delivery_city=row["delivery_city"], status=row["status"], payment_status=row["payment_status"],
                      submitted_at=datetime.fromisoformat(row["submitted_at"]), submission_key=row["submission_key"],
                      status_reason=row["status_reason"] or "",
                      first_replied_at=datetime.fromisoformat(row["first_replied_at"]) if row["first_replied_at"] else None,
                      customer_name=row["customer_name"], customer_email=row["customer_email"],
                      lines=lines[row["id"]], groups=groups[row["id"]])
                for row in rows]
