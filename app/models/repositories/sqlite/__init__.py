"""SQLite implementation of the repositories. The only package in the application that imports sqlite3."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from ..base import Repositories
from .food_items import SqliteFoodItemRepository
from .orders import SqliteOrderRepository
from .users import SqliteUserRepository

SCHEMA = Path(__file__).with_name("schema.sql")

# Columns added after a table first existed. `initialise()` adds them to an older database, so nobody has to rebuild
# it and lose their data (plan 4, P4-10). Only new columns can be handled this way.
ADDED_COLUMNS = {"orders": {"status_reason": "TEXT", "first_replied_at": "TEXT"}}


class Database:
    """Opens one short-lived connection per operation: simple, and safe with Flask's threads."""

    def __init__(self, path):
        self.path = str(path)

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()


class SqliteRepositories(Repositories):
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = Database(path)
        self.users = SqliteUserRepository(self.db)
        self.food_items = SqliteFoodItemRepository(self.db)
        self.orders = SqliteOrderRepository(self.db)

    def initialise(self):
        with self.db.connect() as conn:
            conn.executescript(SCHEMA.read_text(encoding="utf-8"))
            for table, columns in ADDED_COLUMNS.items():
                existing = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
                for name, kind in columns.items():
                    if name not in existing:
                        conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {kind}")

    def reset(self):
        with self.db.connect() as conn:
            conn.execute("PRAGMA foreign_keys = OFF")
            tables = [r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'")]
            for table in tables:
                conn.execute(f'DROP TABLE "{table}"')
        self.initialise()
