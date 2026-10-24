from datetime import datetime

from ...domain import Question, order_number
from ..base import QuestionRepository

# Every question comes with what the staff pages show: the order number, the customer and who answered.
SELECT = ("SELECT q.*, o.submitted_at AS order_submitted_at, c.name AS customer_name, s.name AS answered_by_name"
          " FROM questions q JOIN orders o ON o.id = q.order_id JOIN users c ON c.id = q.customer_id"
          " LEFT JOIN users s ON s.id = q.answered_by")
ORDER = {"waiting": " WHERE q.answered_at IS NULL ORDER BY q.asked_at, q.id",
         "answered": " WHERE q.answered_at IS NOT NULL ORDER BY q.answered_at DESC, q.id DESC",
         "all": " ORDER BY q.answered_at IS NOT NULL, q.asked_at, q.id"}


def _time(value):
    return value.isoformat(sep=" ", timespec="seconds") if value else None


def _parse(value):
    return datetime.fromisoformat(value) if value else None


def to_question(row):
    return Question(id=row["id"], order_id=row["order_id"], customer_id=row["customer_id"], text=row["text"],
                    asked_at=_parse(row["asked_at"]), answer=row["answer"] or "", answered_at=_parse(row["answered_at"]),
                    answered_by=row["answered_by"], customer_name=row["customer_name"],
                    answered_by_name=row["answered_by_name"] or "",
                    order_number=order_number(row["order_id"], _parse(row["order_submitted_at"])))


class SqliteQuestionRepository(QuestionRepository):
    def __init__(self, db):
        self.db = db

    def add(self, question):
        with self.db.connect() as conn:                 # the time comes from the app, not SQLite's UTC clock (P3-11)
            question_id = conn.execute(
                "INSERT INTO questions (order_id, customer_id, text, asked_at, answer, answered_at, answered_by)"
                " VALUES (?, ?, ?, ?, ?, ?, ?)",
                (question.order_id, question.customer_id, question.text, _time(question.asked_at),
                 question.answer or None, _time(question.answered_at), question.answered_by)).lastrowid
        return self.get(question_id)

    def get(self, question_id):
        with self.db.connect() as conn:
            row = conn.execute(SELECT + " WHERE q.id = ?", (question_id,)).fetchone()
            return to_question(row) if row else None

    def list(self, show="waiting"):
        with self.db.connect() as conn:
            return [to_question(row) for row in conn.execute(SELECT + ORDER[show])]

    def save_answer(self, question):
        with self.db.connect() as conn:                 # only if still unanswered: no answer is overwritten (P5-5)
            changed = conn.execute(
                "UPDATE questions SET answer = ?, answered_at = ?, answered_by = ? WHERE id = ? AND answered_at IS NULL",
                (question.answer, _time(question.answered_at), question.answered_by, question.id)).rowcount
        return changed == 1
