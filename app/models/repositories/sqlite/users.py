from ...domain import User, normalise_email
from ..base import UserRepository


def _to_user(row):
    if row is None:
        return None
    return User(id=row["id"], email=row["email"], name=row["name"], role=row["role"],
                password_hash=row["password_hash"])


class SqliteUserRepository(UserRepository):
    def __init__(self, db):
        self.db = db

    def add(self, user):
        with self.db.connect() as conn:
            cur = conn.execute(
                "INSERT INTO users (email, name, password_hash, role) VALUES (?, ?, ?, ?)",
                (normalise_email(user.email), user.name, user.password_hash, user.role))
            return self.get_with(conn, cur.lastrowid)

    def get(self, user_id):
        with self.db.connect() as conn:
            return self.get_with(conn, user_id)

    def get_by_email(self, email):
        with self.db.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE email = ?", (normalise_email(email),)).fetchone()
            return _to_user(row)

    @staticmethod
    def get_with(conn, user_id):
        return _to_user(conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone())
