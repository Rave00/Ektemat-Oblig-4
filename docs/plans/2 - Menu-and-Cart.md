# Plan 2: Customer menu by event and shopping cart

- **Status:** Done. Approved by User1 on 2026-10-21 (no changes requested; P2-5 "fine for now"); built in pull
  request #11, merged by User1 on 2026-10-21.
- **Date:** 2026-10-21
- **Requirements:** C1 (menu by event), C2 (shopping cart). Lab backlog: US-01 (browse the menus by type of event,
  with prices per person; criteria 1-3), US-02 (allergens and dietary labels on every dish; criteria 1 and 3),
  NFR-01 (customer pages load quickly). Follow-up from the NFR-14 check in plan 1: dietary labels that the allergens
  contradict.
- **Builds on:** plan 0 (D5 rules in the model, D7 CSRF, D8 the cart lives in the session) and plan 1 (food items;
  a published dish always has a picture and allergen information).

## 1. What the customer can do afterwards

1. Open the menu (the front page) and see every published dish as a **card**: picture, name, description, price per
   person in NOK, minimum order, allergens as text, and dietary labels (C1, US-01 criterion 1, US-02 criterion 1).
2. See the cards **grouped by event**: one section per kind of event (corporate lunch, conference, julebord,
   wedding, confirmation, birthday). A dish offered for several events is shown in each of those sections (C1).
3. Choose one event to see only its dishes (US-01 criterion 2), and/or a dietary label such as gluten-free to see only
   dishes with that label (US-02 criterion 3).
4. Put a dish in the **cart** with a number of portions, without logging in. The field starts at the dish's minimum
   order; fewer portions are refused with a message that names the minimum (C2).
5. Open the cart: each line shows the dish, price per person, number of portions and line total. Change the number
   or remove the line. The **estimated total** in NOK is shown below the lines (C2).
6. See the number of dishes in the cart in the header ("Cart (2)") on every page.
7. Keep the cart when logging in (needed in plan 3, where the customer logs in to order); logging out empties it.

For staff, one change: a dish can no longer be saved with a dietary label that its allergens contradict, for example
**vegan with eggs or milk** (decision P2-8).

## 2. Screens

| Screen | URL | Notes |
|---|---|---|
| Menu | `/`, `/?event=wedding`, `/?label=gluten_free`, both combined | Short intro, a row of event links ("All events" plus the six events), a row of dietary-label links, then one section of cards per event. The header link "Menu" goes here. |
| Cart | `/cart` | Table of lines with a number field, **Update** and **Remove** per line, and the estimated total. Empty cart: a short message and a link back to the menu. |

Cart actions are POST forms with the CSRF token (team rule): `/cart/add`, `/cart/update`, `/cart/remove`. After each
one the customer is sent back to the page they came from (checked with `safe_next`), with a short message such as
"Added 10 portions of Fish soup with Bergen cod to the cart."

The button that goes from the cart to the order form arrives in plan 3.

## 3. Decisions

| # | Decision | Why | Not chosen |
|---|---|---|---|
| P2-1 | **Cart rules live in the model**, in `app/models/cart.py` (the file plan 0 reserved for them): a `Cart` holds `{dish id: portions}` and has `add`, `set_quantity`, `remove`, `lines` and the estimated total. The number typed by the customer is turned into portions there too. | D5 in plan 0: rules are tested without Flask; `shop.py` only reads the form, calls the cart and shows the messages. | Rules inside the route functions. |
| P2-2 | **Rules for a number of portions:** a whole number, at least the dish's minimum order and at most 1 000. Only published dishes can be added. Adding a dish that is already in the cart adds to its line (10 + 5 = 15), and the sum is checked. | C2: "Quantities below an item's minimum order are not accepted." The upper limit stops typing mistakes such as 10 000 portions (ASSUMPTION: 1 000 is far above the "about 400 covers a day" the event coordinator says the kitchen can make, C-16, so no real order is blocked). | No upper limit; a real capacity check (Sunniva's optional idea, US-10/US-18), which is out of scope. |
| P2-3 | **The session stores only dish ids and portions, never names or prices.** Each page reads the dishes again from the repository, so the cart always shows today's price. A dish that has been unpublished or deleted since is taken out of the cart with a message. If staff raise a minimum order above what is in the cart, the line is kept and marked "below the minimum of 20"; plan 3 refuses to submit it (D8). | Plan 0, D8. The cart never shows an old price or a dish that is no longer for sale, and the customer's numbers are never changed without telling them. The session cookie is signed, so it cannot be edited, and it holds nothing personal. | Storing prices in the session (they would go stale); a cart table in the database (plan 0, D8). |
| P2-4 | **Estimated total = the sum of portions × price per person**, shown with a space between thousands ("12 450 NOK", as in plan 1's "100 000 NOK"), under the heading "Estimated total". A note below says that Ekte Mat confirms the final price when it approves the order, and that discounts and delivery are not included. | C2 asks for an *estimated* total. Discounts are not decided yet (C-12), and some historical totals differ from guests × price (C-17), so the site must not promise an exact price. | Calling it the "Total". |
| P2-5 | **Grouping on the full menu:** sections in the fixed order of `EVENTS` (the same order as the admin form); a section with no dishes is left out. The function that builds the sections, `menu_sections(items, event, label)`, lives in `app/models/domain.py`. | C1: "grouped by kind of event". A customer planning a wedding reads the wedding section and sees everything offered for it, even dishes that are also sold for birthdays. | One flat list with event badges (not grouped); tabs built with JavaScript. |
| P2-6 | **Filters are plain links with query parameters** (`/?event=wedding&label=gluten_free`). An **unknown** event or label code answers 404 instead of showing the full menu. | They work without JavaScript, can be bookmarked and sent to a colleague, and are easy to test. A mistyped `label=glutenfree` that quietly showed every dish would look like a gluten-free list: unsafe for US-02. | Separate pages per event (`/menu/wedding`): more routes, and the label filter still needs a parameter. |
| P2-7 | **Card content and accessibility:** the picture has the dish name as alternative text and loads lazily (`loading="lazy"`); allergens are written out in words (US-02 criterion 1 says "text label"); "Contains none of the 14 allergens" is shown when that box was ticked in plan 1. The number field uses the minimum order as its `min`, as a help only: the server checks the rule (P2-2). Cards sit in a grid that becomes one column on a phone. | Allergy information must be readable, also by screen readers and without colours or icons. Lazy pictures keep the first load small (NFR-01). | Allergen icons only. |
| P2-8 | **Dietary labels that the allergens contradict are refused** when staff save a dish (a new rule in `validate_food_item`): **vegan** cannot contain eggs, milk, fish, crustaceans or molluscs; **vegetarian** cannot contain fish, crustaceans or molluscs; **gluten-free** cannot contain cereals containing gluten. The error is shown next to the dietary labels, for example "A vegan dish can't contain Eggs, Milk." **Lactose-free** with milk stays allowed (lactose-free milk products still contain milk protein), and **halal** has no allergen rule. | Found in the NFR-14 check: Banana Pudding was saved as vegan with eggs and milk. US-02 exists so that customers "can choose safe food for my guests"; a label that contradicts the allergen list misleads them. ASSUMPTION: the rule comes from common food knowledge, not from the data pack; to be confirmed by the product owner. | Only a warning; also checking halal or lactose-free (the allergen list cannot prove those wrong). |
| P2-9 | **Logging in keeps the cart.** `log_in()` still starts a fresh session (against session fixation, as the comment in `security.py` says), but carries the cart across. Logging out empties it. | Plan 3 asks the customer to log in *after* filling the cart (C3: "Log in (or register) and submit the order"). Emptying the cart on log out protects the next person on a shared computer. | Keeping the cart after log out. |
| P2-10 | The header shows **"Cart (n)"**, where n is the number of different dishes, not portions. | "Cart (120)" for a 120-portion buffet would be confusing. | Number of portions. |

**No schema change and no new library.** The seed is unchanged: all 11 sample dishes already pass the rule in P2-8
(checked by a test).

## 4. Files that change

| File | Change |
|---|---|
| `app/models/cart.py` (new) | `Cart`, `CartLine`, `CartError` and the rules in P2-1 to P2-4. |
| `app/models/domain.py` | `menu_sections(...)` (P2-5); the label rule (P2-8) in `validate_food_item`. |
| `app/controllers/shop.py` | Menu with filters, cart page, and the add, update and remove actions. Reads and writes the cart in the session. |
| `app/controllers/security.py` | `log_in()` keeps the cart (P2-9). |
| `app/__init__.py` | A template filter `nok` that writes "12 450 NOK" (P2-4). |
| `app/views/templates/` | `shop/index.html` (menu), `shop/_card.html` (one card), `shop/cart.html`, `base.html` (Cart link with count). |
| `app/views/static/css/style.css` | Cards, filter links and the cart table, including phone width. |
| `tests/` | `test_cart.py` (the cart rules without Flask), `test_menu_and_cart.py` (acceptance tests), and the label rule in `test_food_item_rules.py`. |
| `docs/screenshots/` | Menu (all events and one event, also at phone width) and cart, for the report (Oblig 4, section 5.2). |

## 5. Acceptance tests (written before the code)

**C1, menu by event**
1. Given published and unpublished dishes, When a visitor opens the menu, Then every published dish is shown with
   picture, name, description, price per person in NOK, minimum order and each allergen as text, and the unpublished
   dishes are not shown (US-01 criteria 1 and 3, US-02 criterion 1).
2. Given a dish offered for weddings and birthdays, When the full menu is shown, Then the dish appears in both
   sections, the sections follow the event order, and an event without dishes has no section.
3. Given the visitor chooses "Wedding", When the page is shown, Then only dishes offered for weddings are shown
   (US-01 criterion 2).
4. Given the visitor chooses "Gluten-free", When the page is shown, Then only dishes labelled gluten-free are shown
   (US-02 criterion 3); with an event chosen as well, both filters apply.
5. Given an unknown event or label code in the address, When the page is requested, Then it answers 404.
6. Given a dish marked "contains none of the 14 allergens", When its card is shown, Then it says so.

**C2, shopping cart**
7. Given a visitor who is not logged in, When they add a dish with at least its minimum order, Then the cart shows
   the line with portions, price per person and line total, and the header shows "Cart (1)".
8. Given a number below the minimum, 0, a negative number, a decimal, text or more than 1 000, When it is added or
   used as a new quantity, Then it is refused with a message (naming the minimum where that is the reason) and the
   cart is unchanged (C2).
9. Given a dish already in the cart, When it is added again, Then there is still one line, with the sum of portions.
10. Given a cart line, When the customer changes the number, Then the line total and the estimated total change;
    When they remove the line, Then it is gone and the total no longer includes it.
11. Given several lines, When the cart is shown, Then the estimated total equals the sum of portions × price per
    person, written like "12 450 NOK", and is labelled as an estimate.
12. Given a dish in the cart, When staff unpublish or delete it, Then the next cart page leaves the line out, says
    why, and does not count it.
13. Given a dish in the cart, When staff change its price, Then the cart shows the new price; When staff raise its
    minimum order above the portions in the cart, Then the line is marked as below the new minimum.
14. Given a form posting an unpublished or non-existent dish id to "add" (a tampered form), When it is sent, Then
    nothing is added.
15. Given a cart, When the visitor logs in, Then the cart is kept; When they log out, Then the cart is empty.
16. Given any cart form posted without a valid CSRF token, When it is sent, Then it is refused and the cart is
    unchanged.

**Dietary labels and allergens (P2-8)**
17. Given an admin saving a dish that is vegan with eggs or milk, vegetarian with fish, or gluten-free with gluten,
    When they save, Then nothing is saved and the error is shown next to the dietary labels; lactose-free with milk
    and halal are accepted. Every seed dish passes the rule.

## 6. Out of scope (later plans)

- The order form, logging in or registering to order, guest groups, and prices copied into the order lines (plan 3;
  plan 0, D8).
- Volume discounts (US-07, C-12), children's portions (US-06), and a capacity check for the event date (US-10, C-09,
  C-16).
- A filter that hides dishes containing a chosen allergen ("without nuts"). It would help customers with allergies,
  but it is not in the backlog criteria; it can be added later with the same kind of link as P2-6.
- Norwegian/English texts (US-03; an optional "going further" item in Oblig 4).
- Search, sorting and paging: with about ten dishes they are not needed.

## 7. Risks and open points

- **"Portions" is an ASSUMPTION.** Prices are per person (US-01) and the minimum order is a number of portions, so
  the cart counts portions. If Ekte Mat sells some dishes per tray or package, the word changes; the rules do not.
- **The full menu repeats dishes.** With the seed data it shows 24 cards for 10 published dishes, because most
  dishes belong to several events. The event links at the top keep it easy to use; if it still feels long in the
  browser check, the full menu could jump to the sections instead (a small change to this plan).
- **NFR-01 cannot be measured over 4G here.** Instead: the menu is built from one repository call, pictures are at
  most 1200 px JPEG (plan 1) and load lazily, and the browser check notes the load time.
- **The label rule needs the product owner's confirmation** (P2-8). If they disagree, it is one rule and one test
  to remove.

## 8. Done when

- [x] Acceptance tests 1-17 pass, plus all earlier tests (147 tests).
- [x] Every rule test has been seen to fail when its rule is broken on purpose (as in plan 1).
- [x] Works from a fresh clone with the README commands.
- [x] Works on User1's Windows PC: 147 passed (2026-10-21).
- [x] Checked in a browser at 1200 px and 390 px (page width measured on every page); screenshots of the menu and
      the cart saved in `docs/screenshots/`.
- [x] This plan gets a "What changed compared with the plan" section (below, written with the code).

## 9. What changed compared with the plan (pull request #11)

- **Built as planned:** P2-1 to P2-10 and acceptance tests 1-17 (named `test_p2_at01` to `test_p2_at17`), plus
  model tests for the cart (`test_cart.py`), the menu sections and the label rule (`test_food_item_rules.py`).
- **Small additions found while building:**
  - **Cart lines are sorted by dish name.** The browser check showed lines in the order "1", "10", "5": Flask sorts
    the keys of the session when it saves it, so the order in which dishes were added is lost anyway.
  - **Model tests for `menu_sections`.** Breaking the "published only" check in the model was not noticed by the
    tests through HTTP, because the repository also leaves unpublished dishes out. Both layers are now tested.
  - **The number field accepts at most 7 digits before it is turned into a number.** Python refuses to convert a
    text of more than 4 300 digits, which would have shown an error page instead of a message (a test sends 5 000).
  - The cart page only writes the session when it has taken a dish out.
- **Errors caught before merging:** two of my tests were wrong, not the code. One looked for a dish name that was
  still in the "Removed ..." message (the same mistake as in plan 1); one compared text with an apostrophe that
  Jinja writes as `&#39;`. From the browser check: the header's underline on hover also reached the filter links.
- **Verification:** 147 tests, also from a fresh clone with only the README commands. 17 rules were broken on purpose,
  one at a time, and each was caught by at least one test. Browser check at 1200 px and 390 px: no page is wider than
  the screen; the menu loaded in 71-140 ms locally (NFR-01 cannot be measured over 4G here); no server errors.
- **Windows:** User1 ran the tests on Windows on 2026-10-21: 147 passed.
