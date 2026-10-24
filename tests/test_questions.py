"""Acceptance tests 1-13 of plan 5 (questions on an order), through HTTP and in the model. 14: repository; 15: seed."""
import re
from datetime import datetime, timedelta
from html import unescape

import pytest
from werkzeug.security import generate_password_hash

from app import create_app
from app.models.domain import Question, QuestionError, User, answer_question, validate_question, waiting_time
from conftest import log_in, make_item, make_order, make_question

QUESTION = "Can the food be delivered at 11:30?"


def text(response):
    return unescape(response.get_data(as_text=True))


@pytest.fixture
def order(repos, users):
    dish = repos.food_items.add(make_item(name="Fish soup"))
    return make_order(repos, users["customer"].id, dish.id)


@pytest.fixture
def customer(client, users):
    log_in(client, "kari@test.example")
    return client


# ---- C5, asking and reading -----------------------------------------------------------------------------
def test_p5_at01_a_customer_asks_a_question_on_their_order(customer, repos, order):
    response = customer.post(f"/account/orders/{order.id}/questions", data={"text": f"  {QUESTION}  "})
    assert response.status_code == 302
    [question] = repos.orders.get(order.id).questions
    assert (question.text, question.customer_id, question.answer) == (QUESTION, order.customer_id, "")
    assert question.asked_at is not None
    page = text(customer.get(f"/account/orders/{order.id}"))
    assert QUESTION in page and "Waiting for an answer" in page and "Do not write guest names" in page


@pytest.mark.parametrize("typed, message", [("   ", "Write your question."), ("x" * 1001, "at most 1000 characters")],
                         ids=["empty", "too-long"])
def test_p5_at02_an_empty_or_too_long_question_is_refused(customer, repos, order, typed, message):
    response = customer.post(f"/account/orders/{order.id}/questions", data={"text": typed})
    assert response.status_code == 400 and message in text(response)
    assert repos.orders.get(order.id).questions == []
    if typed.strip():
        assert typed in text(response)                                    # the form keeps what was typed


def test_p5_at03_only_the_orders_customer_can_ask(app, client, admin, repos, order):
    repos.users.add(User(email="nils@test.example", name="Nils", role="customer",
                         password_hash=generate_password_hash("secret-pw")))
    other = app.test_client()
    log_in(other, "nils@test.example")
    assert other.post(f"/account/orders/{order.id}/questions", data={"text": QUESTION}).status_code == 404
    visitor = app.test_client()
    assert visitor.post(f"/account/orders/{order.id}/questions",
                        data={"text": QUESTION}).headers["Location"].startswith("/account/login")
    response = admin.post(f"/account/orders/{order.id}/questions", data={"text": QUESTION})
    assert response.status_code == 403 and "Staff accounts cannot ask questions." in text(response)
    assert repos.orders.get(order.id).questions == []


def test_p5_at04_the_customer_reads_the_answer_and_my_orders_counts_it(app, repos, users, order):
    answered = make_question(repos, order, "Is the soup free of nuts?")
    make_question(repos, order, QUESTION)
    staff = app.test_client()
    log_in(staff, "admin@test.example")
    staff.post(f"/admin/questions/{answered.id}/answer", data={"answer": "Yes, the soup has no nuts."})
    customer = app.test_client()
    log_in(customer, "kari@test.example")
    page = text(customer.get(f"/account/orders/{order.id}"))
    assert "Yes, the soup has no nuts." in page and "Answered by Ekte Mat" in page and "Admin" not in page
    assert "1 answered · 1 waiting" in text(customer.get("/account/orders"))


def test_p5_at05_a_question_with_html_is_shown_as_text(app, customer, repos, order):
    attack = "<script>alert(1)</script>"
    customer.post(f"/account/orders/{order.id}/questions", data={"text": attack})
    staff = app.test_client()                                  # a separate browser: the fixtures share one session
    log_in(staff, "admin@test.example")
    for client, url in ((customer, f"/account/orders/{order.id}"), (staff, f"/admin/orders/{order.id}"),
                        (staff, "/admin/questions")):
        raw = client.get(url).get_data(as_text=True)
        assert attack not in raw and "&lt;script&gt;alert(1)&lt;/script&gt;" in raw, url


# ---- A4, reading and answering --------------------------------------------------------------------------
def test_p5_at06_the_staff_list_shows_waiting_questions_oldest_first(admin, repos, order):
    now = datetime.now().replace(microsecond=0)
    newer = make_question(repos, order, "Newer question", asked_at=now - timedelta(hours=1))
    older = make_question(repos, order, "Older question", asked_at=now - timedelta(hours=30))
    done = make_question(repos, order, "Answered question", asked_at=now - timedelta(days=3),
                         answer="Yes.", answered_at=now - timedelta(days=2))
    page = text(admin.get("/admin/questions"))
    shown = re.findall(r'data-question="(\d+)"', page)
    assert shown == [str(older.id), str(newer.id)] and order.number in page and "Kari" in page
    assert "30 hours" in page and "Waiting (2)" in page and "Answered (1)" in page and "All (3)" in page
    assert re.findall(r'data-question="(\d+)"', text(admin.get("/admin/questions?show=answered"))) == [str(done.id)]
    assert len(re.findall(r'data-question="(\d+)"', text(admin.get("/admin/questions?show=all")))) == 3
    assert admin.get("/admin/questions?show=new").status_code == 404


def test_p5_at07_the_staff_order_page_shows_the_questions_with_answer_forms(admin, repos, order):
    waiting = make_question(repos, order, QUESTION)
    make_question(repos, order, "Answered one", answer="Yes.", answered_at=datetime.now())
    page = text(admin.get(f"/admin/orders/{order.id}"))
    assert QUESTION in page and "Answered one" in page and "Yes." in page
    assert re.findall(r'action="/admin/questions/(\d+)/answer"', page) == [str(waiting.id)]


def test_p5_at08_staff_answer_a_question(admin, repos, users, order):
    question = make_question(repos, order)
    for bad in ("  ", "x" * 2001):
        response = admin.post(f"/admin/questions/{question.id}/answer", data={"answer": bad})
        assert response.status_code == 400 and repos.questions.get(question.id).answer == ""
    response = admin.post(f"/admin/questions/{question.id}/answer", data={"answer": " Yes, 11:30 is fine. "})
    assert response.headers["Location"].startswith(f"/admin/orders/{order.id}")
    saved = repos.questions.get(question.id)
    assert (saved.answer, saved.answered_by) == ("Yes, 11:30 is fine.", users["admin"].id) and saved.answered_at


def test_p5_at09_an_answered_question_cannot_be_answered_again(admin, repos, order):
    question = make_question(repos, order)
    admin.post(f"/admin/questions/{question.id}/answer", data={"answer": "First answer."})
    page = text(admin.post(f"/admin/questions/{question.id}/answer", data={"answer": "Second answer."},
                           follow_redirects=True))
    assert "already been answered" in page and repos.questions.get(question.id).answer == "First answer."


# (Acceptance test 10, customers and visitors on every /admin/questions page, is test_at10 in test_admin_items.py.)


def test_p5_at11_the_dashboard_counts_waiting_questions(admin, repos, order):
    make_question(repos, order)
    make_question(repos, order, "Answered", answer="Yes.", answered_at=datetime.now())
    page = text(admin.get("/admin/"))
    assert re.search(r'stat-value">1</span><span class="stat-label">question waiting for an answer', page)
    assert 'href="/admin/questions"' in page


def test_p5_at12_question_and_answer_forms_need_the_csrf_token(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "csrf.db")})   # CSRF on
    client = app.test_client()
    assert client.post("/account/orders/1/questions", data={"text": QUESTION}).status_code == 400
    assert client.post("/admin/questions/1/answer", data={"answer": "Yes."}).status_code == 400


# ---- the rules in the model (acceptance test 13) --------------------------------------------------------
def test_p5_at13_question_and_answer_rules():
    assert validate_question(f"  {QUESTION}\n") == QUESTION
    for bad in ("", "   ", "x" * 1001):
        with pytest.raises(QuestionError):
            validate_question(bad)
    assert validate_question("x" * 1000) == "x" * 1000
    now = datetime(2026, 10, 24, 10, 0)
    question = Question(order_id=1, customer_id=2, text=QUESTION, asked_at=now - timedelta(hours=2), id=5)
    answered = answer_question(question, " Yes. ", staff_id=9, now=now)
    assert (answered.answer, answered.answered_by, answered.answered_at) == ("Yes.", 9, now)
    assert question.answer == "" and answered.answered
    for bad in ("", "x" * 2001):
        with pytest.raises(QuestionError):
            answer_question(question, bad, staff_id=9, now=now)
    with pytest.raises(QuestionError, match="already been answered"):
        answer_question(answered, "Again.", staff_id=9, now=now)


@pytest.mark.parametrize("hours, shown", [(0.001, "less than a minute"), (0.2, "12 minutes"), (1, "1 hour"),
                                          (5.5, "5 hours"), (30, "30 hours"), (72, "3 days")])
def test_waiting_time_reads_like_a_person_would_say_it(hours, shown):
    now = datetime(2026, 10, 24, 10, 0)
    assert waiting_time(now - timedelta(hours=hours), now) == shown
