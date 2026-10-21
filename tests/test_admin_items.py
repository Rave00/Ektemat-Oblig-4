"""Acceptance tests 1-14 of plan 1 (food items and pictures in the admin panel), through HTTP."""
import io

import pytest
from PIL import Image

from conftest import log_in, make_item, picture

FORM = {"name": "Fish soup", "description": "Creamy soup", "price_nok": "189", "min_order_qty": "10",
        "events": ["conference"], "allergens": ["fish", "milk"]}


def upload(admin, item_id, data, filename="photo.jpg"):
    return admin.post(f"/admin/items/{item_id}/image", data={"image": (io.BytesIO(data), filename)},
                      content_type="multipart/form-data")


def test_at01_a_valid_new_item_is_added_unpublished(admin, repos):
    response = admin.post("/admin/items/new", data=FORM)
    assert response.status_code == 302
    [item] = repos.food_items.list()
    assert (item.name, item.price_nok, item.events, item.published) == ("Fish soup", 189, ["conference"], False)
    assert b"Fish soup" in admin.get("/admin/items").data


def test_at02_invalid_fields_are_shown_and_nothing_is_saved(admin, repos):
    bad = {**FORM, "name": "", "price_nok": "-1", "min_order_qty": "0", "events": []}
    response = admin.post("/admin/items/new", data=bad)
    assert response.status_code == 400
    for message in (b"Enter a name.", b"between 0 and 100 000 NOK", b"between 1 and 1000", b"Tick at least one event."):
        assert message in response.data
    assert repos.food_items.list() == []


def test_at02_text_in_a_number_field_is_refused(admin, repos):
    response = admin.post("/admin/items/new", data={**FORM, "price_nok": "cheap"})
    assert response.status_code == 400 and b"Enter a whole number." in response.data
    assert b'value="cheap"' in response.data                   # the form keeps what was typed


def test_at03_a_tampered_allergen_code_is_refused(admin, repos):
    response = admin.post("/admin/items/new", data={**FORM, "allergens": ["fish", "chocolate"]})
    assert response.status_code == 400 and b"Unknown value: chocolate." in response.data
    assert repos.food_items.list() == []


def test_at04_a_change_is_stored_and_visible_on_the_front_page(admin, repos):
    item = repos.food_items.add(make_item(image_path="uploads/a.jpg", published=True))
    response = admin.post(f"/admin/items/{item.id}/edit",
                          data={**FORM, "price_nok": "205", "events": ["wedding", "birthday"],
                                "allergens": ["fish"], "published": "on"})
    assert response.status_code == 302
    saved = repos.food_items.get(item.id)
    assert (saved.price_nok, saved.events, saved.allergens) == (205, ["birthday", "wedding"], ["fish"])
    assert b"205 NOK per person" in admin.get("/").data


def test_at05_publishing_without_allergen_information_is_blocked(admin, repos):
    item = repos.food_items.add(make_item(allergens=[], image_path="uploads/a.jpg", published=False))
    admin.post(f"/admin/items/{item.id}/publish")
    assert b"Allergen information missing" in admin.get("/admin/items").data
    assert not repos.food_items.get(item.id).published


def test_at05_the_edit_form_also_blocks_publishing(admin, repos):
    item = repos.food_items.add(make_item(allergens=[], image_path="uploads/a.jpg"))
    response = admin.post(f"/admin/items/{item.id}/edit", data={**FORM, "allergens": [], "published": "on"})
    assert response.status_code == 400 and b"Cannot publish: Allergen information missing." in response.data


def test_at06_publishing_without_a_picture_is_blocked(admin, repos):
    item = repos.food_items.add(make_item(image_path=None, published=False))
    admin.post(f"/admin/items/{item.id}/publish")
    assert b"Picture missing" in admin.get("/admin/items").data
    assert not repos.food_items.get(item.id).published


def test_at07_publish_and_unpublish_control_the_front_page(admin, repos):
    item = repos.food_items.add(make_item(name="Lamb from Voss", image_path="uploads/a.jpg", published=False))
    # follow_redirects: like a browser, so the flash message is shown on the food items page, not on "/"
    admin.post(f"/admin/items/{item.id}/publish", follow_redirects=True)
    assert b"Lamb from Voss" in admin.get("/").data
    admin.post(f"/admin/items/{item.id}/unpublish", follow_redirects=True)
    assert b"Lamb from Voss" not in admin.get("/").data


def test_at08_a_deleted_item_is_gone(admin, repos, app, tmp_path):
    stored = tmp_path / "uploads" / "old.jpg"
    stored.parent.mkdir(parents=True)
    stored.write_bytes(picture())
    item = repos.food_items.add(make_item(name="Old soup", image_path="uploads/old.jpg", published=True))
    admin.post(f"/admin/items/{item.id}/delete", follow_redirects=True)
    assert repos.food_items.get(item.id) is None
    assert b"Old soup" not in admin.get("/").data
    assert not stored.exists(), "the picture file is deleted with the item"


def test_at09_an_item_in_an_order_cannot_be_deleted(admin, repos, users):
    item = repos.food_items.add(make_item(name="Wedding dinner"))
    with repos.db.connect() as conn:                       # orders arrive in plan 3; add one by hand
        order = conn.execute("INSERT INTO orders (customer_id, event_date, event_type, guest_count, delivery_address) "
                             "VALUES (?, '2027-06-19', 'wedding', 120, 'Testgata 1, Bergen')", (users["customer"].id,))
        conn.execute("INSERT INTO order_lines (order_id, food_item_id, quantity, unit_price_nok) VALUES (?, ?, 120, 875)",
                     (order.lastrowid, item.id))
    admin.post(f"/admin/items/{item.id}/delete")
    assert repos.food_items.get(item.id) is not None
    assert b"is part of an order and cannot be deleted. Unpublish it instead." in admin.get("/admin/items").data


def admin_urls(app, item_id):
    """Every GET and POST address in the admin panel, including routes added after this test was written."""
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith("admin."):
            url = rule.rule.replace("<int:item_id>", str(item_id))
            for method in sorted(rule.methods & {"GET", "POST"}):
                yield method, url


def test_at10_customers_and_visitors_cannot_use_any_admin_page(app, client, repos, users):
    item = repos.food_items.add(make_item(name="Untouched", published=False))
    urls = list(admin_urls(app, item.id))
    assert len(urls) >= 11
    for method, url in urls:
        response = client.open(url, method=method, data=FORM)
        assert response.status_code == 302 and "/account/login" in response.headers["Location"], (method, url)
    log_in(client, "kari@test.example")
    for method, url in urls:
        assert client.open(url, method=method, data=FORM).status_code == 403, (method, url)
    assert repos.food_items.list() == [item], "nothing may change"


def test_at11_upload_shows_a_preview_and_changes_nothing_yet(admin, repos):
    item = repos.food_items.add(make_item(image_path="uploads/old.jpg"))
    response = upload(admin, item.id, picture())
    assert response.headers["Location"].endswith(f"/admin/items/{item.id}/image/preview")
    page = admin.get(f"/admin/items/{item.id}/image/preview")
    assert page.status_code == 200 and b"uploads/pending/" in page.data
    assert repos.food_items.get(item.id).image_path == "uploads/old.jpg"


def test_at12_save_uses_the_new_picture_and_cleans_up(admin, repos, tmp_path):
    folder = tmp_path / "uploads"
    folder.mkdir()
    (folder / "old.jpg").write_bytes(picture())
    item = repos.food_items.add(make_item(image_path="uploads/old.jpg"))
    upload(admin, item.id, picture(colour="blue"))
    admin.post(f"/admin/items/{item.id}/image/save")
    new_path = repos.food_items.get(item.id).image_path
    assert new_path.startswith("uploads/") and new_path != "uploads/old.jpg"
    assert (tmp_path / new_path).is_file()
    assert not (folder / "old.jpg").exists()
    assert list((folder / "pending").iterdir()) == []


def test_at13_discard_changes_nothing_and_removes_the_upload(admin, repos, tmp_path):
    item = repos.food_items.add(make_item(image_path="uploads/old.jpg"))
    upload(admin, item.id, picture())
    admin.post(f"/admin/items/{item.id}/image/discard")
    assert repos.food_items.get(item.id).image_path == "uploads/old.jpg"
    assert list((tmp_path / "uploads" / "pending").iterdir()) == []


def test_at14_a_text_file_named_jpg_is_refused(admin, repos, tmp_path):
    item = repos.food_items.add(make_item())
    response = upload(admin, item.id, b"this is not a picture", "photo.jpg")
    assert response.headers["Location"].endswith(f"/admin/items/{item.id}/edit")
    assert b"not a JPEG, PNG or WebP picture" in admin.get(f"/admin/items/{item.id}/edit").data
    assert not (tmp_path / "uploads" / "pending").exists()


def test_at14_a_file_above_the_upload_limit_gets_a_clear_message(admin, repos):
    item = repos.food_items.add(make_item())
    response = upload(admin, item.id, b"0" * (3 * 1024 * 1024))
    assert response.status_code == 413 and b"pictures can be at most 2 MB" in response.data


def test_uploading_twice_keeps_only_the_latest_pending_picture(admin, repos, tmp_path):
    item = repos.food_items.add(make_item())
    upload(admin, item.id, picture(colour="red"))
    upload(admin, item.id, picture(colour="blue"))
    pending = list((tmp_path / "uploads" / "pending").iterdir())
    assert len(pending) == 1 and Image.open(pending[0]).getpixel((5, 5))[2] > 200      # the blue one


@pytest.mark.parametrize("url", ["/admin/items/999/edit", "/admin/items/999/image/preview"])
def test_unknown_items_give_404(admin, url):
    assert admin.get(url).status_code == 404
