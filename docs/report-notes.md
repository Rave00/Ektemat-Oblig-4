# Notes for the Oblig 4 report

Working notes, collected while building, in the order of the report (Oblig 4, section 5). Every feature pull request
updates this file. Facts here point to a plan, a pull request (#) or a file, so they can be checked.
No names of group members in this file (team rule in `CLAUDE.md`); they go on the PDF only.

## 1. Front page

| Item | Value |
|---|---|
| Group members | Written on the PDF only. |
| GitHub repository | Link written on the PDF. |
| Version to assess | Tag **`Obligatorisk-4`** (GitHub release "Obligatorisk 4 - Ekte Mat", commit `14caa3a`, the merge of pull request #19). All of C1-C5 and A1-A4 built; 305 tests. |
| Neo4j included? | No, unless plan 6 is built before the tag (Oblig 4: then the submission also counts as Oblig 5). |

## 2. Features and screenshots

| Feature | One line | Plan | Screenshots (`docs/screenshots/`) | Status |
|---|---|---|---|---|
| Food items (A1) | Staff add, edit, publish and remove dishes with price, minimum order, events, allergens and dietary labels. | 1 | `plan1-food-items.png`, `plan1-add-form-with-errors.png`, `plan1-edit-food-item.png` | Done |
| Images (A2) | Staff upload a picture, compare it with the current one, then save or discard it. | 1 | `plan1-picture-preview.png` | Done |
| Menu by event (C1) | Dishes as cards grouped by event, with event and dietary-label filters. | 2 | `plan2-menu.png`, `plan2-menu-wedding.png`, `plan2-menu-phone.png` | Done |
| Shopping cart (C2) | Add, change and remove dishes; the minimum order is enforced; estimated total in NOK. | 2 | `plan2-cart.png`, `plan2-cart-phone.png` | Done |
| Register and order (C3) | Register or log in from the cart, then send event, date, guests, address and guest groups; the order page is the receipt. | 3 | `plan3-register.png`, `plan3-order-form.png`, `plan3-order-form-errors.png`, `plan3-order-page.png`, `plan3-order-form-phone.png`, `plan3-order-page-phone.png` | Done |
| My orders (C4) | The customer's orders with order status, payment status and total; a rejection shows its reason. | 4 | `plan4-my-orders.png`, `plan4-my-orders-phone.png` | Done |
| Orders (A3) | All orders, filtered by status and event date, late replies highlighted; a page per order with only the allowed status changes, and the payment status. | 4 | `plan4-order-list.png`, `plan4-order-list-filtered.png`, `plan4-order-page-admin.png`, `plan4-order-page-admin-phone.png`, `plan4-dashboard.png` | Done |
| Questions (C5, A4) | Customers ask about an order on its page and read the answer; staff see the longest-waiting question first and answer once. | 5 | `plan5-order-questions.png`, `plan5-order-questions-phone.png`, `plan5-admin-questions.png`, `plan5-admin-questions-phone.png`, `plan5-admin-order-questions.png` | Done |

Screens the report must show (section 5.2): all nine are done: menu, cart, order form, my orders, questions, food
item, image, order list and order page.

## 3. Software design: what was used and how

| Design concept | File | How it was used |
|---|---|---|
| User stories with acceptance criteria | `docs/requirements/EkteMat_backlog_v3.xlsx` | Every plan starts from stories (for example US-01, US-02, US-47). Their Given/When/Then criteria became acceptance tests written before the code; US-02's message "Allergen information missing" is tested word for word. |
| Non-functional requirements | same file | NFR-14 (a dish added in 3 minutes) was checked by hand in plan 1; NFR-20 (order data rules) shapes plan 3; NFR-19 (store the first reply time, show the share answered within 24 hours) became the dashboard table in plan 4, which makes NFR-05's 95 % target measurable. |
| Use-case diagram | `docs/design/02_uml_use-case.*` | Maps actors to the features A1-A4 and C1-C5; used to decide the scope and order of the plans (plan 0, section 5). |
| Domain class diagram | `docs/design/02_uml_domain-class.*`, `02_uml_domain-enums.*` | The tables in plan 0 are a subset of it (Dish, Order, OrderLine, GuestGroup); six of its seven EventType values became the events on the menu ("OtherParty" was left out). |
| State machine for the order | `docs/design/02_uml_state-order.*` | Basis for the order statuses (plan 0, D10), simplified to the names in Oblig 4. In plan 4 its transitions became a table in `app/models/order_status.py`; the staff page shows one button per allowed transition, and every other change is refused. |
| BPMN TO-BE process | `docs/design/02_bpmn_tobe-order-process.*` | The process the site supports: the customer sends a request online, staff approve it. |
| MVC architecture | plan 0, section 2; `tests/test_architecture.py` | Folders `models`, `views`, `controllers`; a test fails if SQLite is used outside the repository classes, so Neo4j can replace it (plan 6). |
| Data analysis rules V1-V10 | lab `04_report_order-data-quality.md`; plan 3, section 4 | Ten problems found in 820 rows of old orders became form rules and database checks, for example "guests 1-400" (V5, V6) and "postcode four digits" (V10), which is why the address has three fields. |
| Graph data model | plan 6 (draft) | How the same data will look in Neo4j for Oblig 5. |

## 4. Did design help? Evidence collected while building

**Where design work changed the product**
- **Plan 0 (before any code):** planning the feature order showed that the admin pages in plan 1 need a log in, so
  log in moved from plan 3 into plan 0.
- **US-02 → plan 1:** the criterion "publishing is blocked ... 'Allergen information missing'" led to an explicit
  "contains none of the 14 allergens" box, so a dish with no allergens is not mistaken for one with missing information.
- **NFR-14 → plan 2:** timing the hand check of NFR-14 also showed that a dish could be saved as vegan with eggs and
  milk. US-02's goal ("choose safe food for my guests") justified a new rule (P2-8), marked as an assumption.
- **US-47 criterion 3 → plan 2:** "the cart is still there afterwards" showed, while planning, that logging in wiped
  the cart. It was fixed in plan 2 (P2-9), before plan 3 needed it.
- **Data analysis → plan 3:** the lab's V1-V10 became validation rules and database checks; V1 (orders entered
  twice) led to protection against double clicks (P3-7), and V10 (wrong postcodes) split the address into three fields.
- **US-40 and the GDPR note → plan 3:** allergies are stored per guest group with a count, and the order form has no
  name field and asks customers not to write names.
- **Plan 6's promise → plan 3:** plan 6 (P6-7) had asked for one storage-neutral error for a taken e-mail address;
  plan 3 added it, so the registration page does not depend on SQLite.
- **Repository pattern (plan 0, D3-D4) → plan 6:** a teammate could plan the Neo4j storage without touching any page
  or route.
- **State machine → plan 4:** drawing the order's states in the lab gave the exact table of allowed changes; the
  staff page cannot offer a jump such as Submitted → Delivered (the old data had a status typo, V3).
- **US-19 → plan 4:** "a reason is required and sent to the customer" led to a reason field and to showing it on
  the customer's order page, since there is no e-mail yet.
- **US-21 → plan 5:** "the whole conversation is kept with the order" put the questions on the order pages, not on a
  page of their own; the `questions` table designed in plan 0 fitted as it was, so plan 5 needed no database change.
- **NFR-19 → plan 4:** the lab analysis showed reply times could not be measured ("only as a manually typed
  number"); storing the first status change makes the 24-hour target checkable per month.

**Where Claude Code needed steering or got something wrong** (caught before merging unless noted)
- Plan 1 was merged while it still said "draft" (#2). Since plan 2, the status line is updated before the merge.
- Tests that looked for text which was also in a flash message: plan 1 and again in plan 2.
- A test whose generated name contained 2 MB of data broke on Windows; a teammate found and fixed it (#5). Since then, User1 runs the tests on
  Windows before merging.
- Plan 0 named a code attribute that was never used, and plan 6 brought back the owner's real name. Both were found
  in a review of the whole repository (#8).
- Bugs that only the browser check found: a file picker wider than its column (plan 1), and cart lines in a strange
  order (plan 2).
- Breaking each rule on purpose found a gap in the tests: in plan 2, the menu's "published only" check in the model
  was untested. In plan 3 all 218 tests passed at once, so the same check (22 rules) was used to show they really
  test something.
- Plan 3: the README first quoted an error message from memory; it was checked against an old database and corrected.
  The browser check found the order form too wide for a phone, and screenshots with American dates.
- Plan 4: a Python trap (a method called `list` hid the built-in `list`) stopped every test; the browser check found
  a status form that sent no status when submitted without its button, and red buttons shown in green.
- Plan 5: two of my tests were wrong (one compared an order with itself, one let two fixtures share a session); the
  browser check showed that plan 4's dashboard repeated every number.
- Plan 4's mutation check showed why one small test change mattered: "the payment form is open to everyone" was
  caught only because the every-admin-route test was extended to the new order pages. The same happened in plan 5
  for "answering questions is open to everyone".

**Decisions made by the team, not the agent:** SQLite for Oblig 4 and Neo4j later; every plan approved before code
(plan 0 with a file-name change; plans 1-3 with no changes, P2-5 "fine for now"); guest groups, strict event
matching, double-click protection and customer-only ordering confirmed in plan 3; the owner called User1 in every file; course staff access not
needed.

**Numbers:** tests after each plan: 22 (plan 0), 71 (plan 1 and the privacy test), 147 (plan 2), 218 (plan 3),
282 (plan 4), 305 (plan 5).
