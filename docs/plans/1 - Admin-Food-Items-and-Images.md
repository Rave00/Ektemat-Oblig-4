# Plan 1: Admin food items and images

- **Status:** DRAFT, awaiting approval by Rave
- **Date:** 2026-10-21
- **Requirements:** A1 (food items), A2 (images). Lab backlog: US-25 (staff edit the menu themselves),
  US-02 (allergens; publishing blocked without allergen information), NFR-14 (a dish added in at most 3 minutes).
- **Builds on:** plan 0 (log in, `admin_required`, repositories, CSRF).

## 1. What the admin can do afterwards

1. See all food items in a table: picture, name, price, minimum order, events, published or not.
2. Add a food item and edit it: name, description, price in NOK, minimum order quantity, events, allergens,
   dietary labels.
3. Publish and unpublish an item. Publishing is refused, with a clear reason, if the item has no picture or no
   allergen information.
4. Delete an item, after a confirmation. Refused if the item is part of an order (from plan 3 on); the admin is
   told to unpublish it instead.
5. Upload a picture, see a preview next to the current picture, then **Save** or **Discard**. Nothing changes
   until Save (A2).

## 2. Screens

| Screen | URL | Notes |
|---|---|---|
| Food items | `/admin/items` | Table with thumbnails; buttons Edit, Publish/Unpublish, Delete; link "Add food item". |
| Add / edit food item | `/admin/items/new`, `/admin/items/<id>/edit` | One form for both. Errors next to the fields; the form keeps what was typed. |
| Picture preview | `/admin/items/<id>/image/preview` | Current picture and new picture side by side; Save / Discard. |

The admin dashboard (plan 0) links to the food items page.

## 3. Decisions

| # | Decision | Why |
|---|---|---|
| P1-1 | **Validation rules live in the model** (`app/models/domain.py`): name 1-100 characters, description 1-500, price 0-100 000 NOK, minimum order 1-1000, at least one event, only known codes for events, allergens and labels. | One place for the rules, tested without Flask; the controller only turns the form into a `FoodItem` and shows the errors. |
| P1-2 | **"Contains none of the 14 allergens"** is an explicit tick box (new column `no_allergens`). Allergen information counts as given when at least one allergen is ticked **or** this box is ticked; both at once is an error. | US-02: an empty allergen list must not be published by mistake, but some dishes really have no allergens. |
| P1-3 | **Publishing rules** (`publish_problems(item)` in the model): "Allergen information missing" (US-02, exact wording) and "Picture missing" (C1: every menu card shows a picture). New items start unpublished. | The rule is checked both on the Publish button and on the edit form's "Published" box. |
| P1-4 | **Pictures are handled in the model layer** by a small `ImageStore` (`app/models/images.py`): it checks the file with Pillow (JPEG, PNG or WebP, at most 2 MB and 40 megapixels), re-saves it as JPEG at most 1200 px wide, and gives it a random file name. | Re-saving removes hidden metadata such as GPS position from phone photos and anything that is not a real picture. Random names mean a user can never choose a file path. |
| P1-5 | **Preview flow:** upload -> stored as *pending* (folder `uploads/pending/`, name remembered in the session) -> preview page -> Save moves it into place and deletes the old picture, Discard deletes it. | A2 requires a preview before saving. The same flow can later take a picture created by an AI service (optional plan) instead of an upload. |
| P1-6 | **Delete is refused for items in an order** (a repository method `is_ordered(id)`). Tested now by adding an order row directly in the test. | Old orders must keep pointing at the dish they ordered; unpublishing hides it from the menu instead. |
| P1-7 | Confirmation before Delete with the browser's built-in confirm box. | One line, no extra page. |

**Schema change:** `food_items` gets `no_allergens INTEGER NOT NULL DEFAULT 0`. After pulling, run `python seed.py`
once (it rebuilds the database). The seed marks every sample dish's allergen information as given.

## 4. Acceptance tests (written before the code)

**A1, food items**
1. Given an admin, When they submit a valid new item, Then it appears in the food items table, unpublished.
2. Given the form, When the name is empty, the price is -1, the minimum order is 0 or no event is ticked,
   Then each error is shown next to its field and nothing is saved.
3. Given a form posted with an unknown allergen code (a tampered form), When it is submitted, Then it is refused.
4. Given an item, When the admin changes price, events and allergens and saves, Then the new values are stored
   and the change is visible on the customer front page (US-25, criterion 1).
5. Given an item with no allergen information, When the admin publishes it, Then publishing is blocked with
   "Allergen information missing" (US-02, criterion 2).
6. Given an item without a picture, When the admin publishes it, Then publishing is blocked with "Picture missing".
7. Given an item with a picture and allergen information, When the admin publishes it, Then it is shown on the
   front page; after Unpublish it is not.
8. Given an item, When the admin deletes it, Then it is gone from the table and the front page.
9. Given an item that is part of an order, When the admin deletes it, Then it is kept and the admin is told to
   unpublish it instead.
10. Given a customer or a visitor, When they open or post to any `/admin/items` page, Then they get 403 or are
    sent to log in, and nothing changes.

**A2, images**
11. Given an item, When the admin uploads a JPEG or PNG, Then the preview page shows the new picture and the
    item still has its old picture.
12. Given the preview, When the admin clicks Save, Then the item uses the new picture, the old uploaded picture
    and the pending file are deleted.
13. Given the preview, When the admin clicks Discard, Then the item is unchanged and the pending file is deleted.
14. Given a text file renamed to `.jpg`, a file above 2 MB or a picture above 40 megapixels, When it is
    uploaded, Then it is refused with a message and nothing is stored.
15. Given a JPEG with GPS metadata, When it is uploaded and saved, Then the stored picture has no metadata.

## 5. Out of scope (later plans)

- The customer menu with cards and the cart (plan 2).
- Prices frozen in submitted orders (plan 3; US-25 criterion 2).
- Creating or changing a picture from a written instruction to an AI service (A2's alternative): a possible
  optional plan, using the same pending and preview flow (P1-5).
- Norwegian/English texts (US-03), suppliers and origin (US-04, US-26).

## 6. Done when

- [ ] Acceptance tests 1-15 pass, plus all earlier tests.
- [ ] Works from a fresh clone with the README commands.
- [ ] Checked in a browser, including phone width; screenshots of the food items table, the form and the
      picture preview are saved for the report.
- [ ] NFR-14 checked by hand: adding a dish with a picture takes less than 3 minutes.
- [ ] This plan gets a "What changed compared with the plan" section after merging.
