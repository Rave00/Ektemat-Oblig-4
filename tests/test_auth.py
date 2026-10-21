"""Log in, log out and access rules (plan 0, D6 and D7)."""
from app import create_app
from conftest import log_in


def test_admin_can_log_in_and_open_the_admin_panel(client, users):
    response = log_in(client, "admin@test.example")
    assert response.status_code == 302
    assert client.get("/admin/").status_code == 200


def test_wrong_password_gives_the_same_message_as_unknown_email(client, users):
    wrong_password = log_in(client, "admin@test.example", "nope")
    unknown_email = log_in(client, "nobody@test.example")
    for response in (wrong_password, unknown_email):
        assert response.status_code == 401
        assert b"Wrong e-mail or password." in response.data


def test_customer_gets_403_in_the_admin_panel(client, users):
    log_in(client, "kari@test.example")
    assert client.get("/admin/").status_code == 403


def test_visitor_is_sent_to_log_in_from_the_admin_panel(client):
    response = client.get("/admin/")
    assert response.status_code == 302
    assert "/account/login?next=/admin/" in response.headers["Location"]


def test_log_in_returns_to_the_page_asked_for_but_never_to_another_site(client, users):
    ok = client.post("/account/login", data={"email": "admin@test.example", "password": "secret-pw", "next": "/admin/"})
    assert ok.headers["Location"].endswith("/admin/")
    client.post("/account/logout")
    for evil in ("https://evil.example", "//evil.example", "/\\evil.example"):
        response = client.post("/account/login",
                               data={"email": "admin@test.example", "password": "secret-pw", "next": evil})
        assert response.headers["Location"] == "/", evil
        client.post("/account/logout")


def test_log_out_ends_the_session(client, users):
    log_in(client, "admin@test.example")
    client.post("/account/logout")
    assert client.get("/admin/").status_code == 302


def test_a_post_without_the_csrf_token_is_refused(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "csrf.db")})   # CSRF switched on
    response = app.test_client().post("/account/login", data={"email": "a@b.example", "password": "x"})
    assert response.status_code == 400


def test_a_post_with_the_csrf_token_is_accepted(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "test-key", "DATABASE": str(tmp_path / "csrf.db")})
    client = app.test_client()
    client.get("/account/login")
    with client.session_transaction() as session:
        token = session["_csrf"]
    response = client.post("/account/login", data={"email": "a@b.example", "password": "x", "csrf_token": token})
    assert response.status_code == 401          # reached the log in check: the token was accepted
