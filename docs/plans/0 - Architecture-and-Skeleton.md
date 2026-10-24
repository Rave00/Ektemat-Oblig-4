# Plan 0: Architecture and walking skeleton

- **Status:** Done. Approved by User1 on 2026-10-21 (only change requested: the file name); built in pull request #1, merged by User1 on 2026-10-21.
  Revised the same day, before any code: log in / log out moved into plan 0 (see section 5, "Revision").
- **Date:** 2026-10-21
- **Covers:** the overall architecture of Ekte Mat Online (Oblig 4) and the first build step. Every later feature gets its own plan (`1 - ...`, `2 - ...`) before it is built.

## 1. Goal

A working first version of Ekte Mat Online: a customer site and an admin panel in Flask, following MVC, with
SQLite as a temporary store behind repository classes, so that Neo4j can replace it in Oblig 5 without touching
controllers or views.

**In scope (Oblig 4 minimum):** admin A1 food items, A2 images, A3 orders, A4 questions; customer C1 menu by
event, C2 cart, C3 order (with login/registration), C4 my orders, C5 questions. Seed script, README, tests.

**Out of scope for now:** payment, Neo4j (Oblig 5), company accounts, kitchen view and capacity check (candidates
for optional plans once the minimum works).

## 2. Architecture (MVC, visible in the folder structure)

```
ektemat-online/
  CLAUDE.md                  project briefing for Claude Code
  README.md                  install, seed, run, test
  requirements.txt           Flask, Pillow, pytest (nothing else)
  .env.example               settings template; the real .env is never committed
  seed.py                    synthetic food items, one admin, test customers
  app/
    __init__.py              create_app(): config, blueprints, repositories
    models/                  MODEL: domain classes and all data access
      domain.py              FoodItem, User, Order, OrderLine, GuestGroup, Question (plain dataclasses)
      order_status.py        allowed status transitions (the state machine)
      cart.py                cart rules: minimum order, estimated total
      repositories/
        base.py              repository interfaces (what controllers may call)
        sqlite/              the ONLY code that touches SQLite (schema.sql + one class per aggregate)
    controllers/             CONTROLLER: Flask routes in blueprints
      shop.py                menu, cart                      (C1, C2)
      account.py             register, login, order, my orders, questions   (C3, C4, C5)
      admin.py               food items, images, orders, questions          (A1-A4)
      security.py            login_required, admin_required, CSRF check
    views/                   VIEW: Jinja2 templates and static files
      templates/  base.html, shop/, account/, admin/
      static/     css/, js/, uploads/ (uploaded images, not in Git)
  tests/                     pytest: models, repositories, each blueprint, architecture rules
  docs/
    plans/                   one approved plan per larger feature: "N - Name-With-Dashes.md"
    design/                  diagrams carried over from the lab and updated
  .claude/skills/ektemat-requirements/   team requirements skill from the lab
```

## 3. Decisions

| # | Decision | Why | Alternative not chosen |
|---|---|---|---|
| D1 | Flask app factory with three blueprints: `shop`, `account`, `admin`. Templates live in `app/views/` (Flask is told where). | The three MVC layers are visible as three folders, as the assignment requires. | Flask's default `app/templates`: hides the View layer. |
| D2 | SQLite through Python's built-in `sqlite3`, **no ORM**. | Fewer moving parts, and all SQL sits in one package, which is exactly the part Oblig 5 replaces. | SQLAlchemy: maps data access into the model classes, blurring the boundary Neo4j needs. |
| D3 | **Repository pattern.** Controllers get repositories from one factory (`current_app.repos`) and only call the interfaces in `base.py`. | Swapping to Neo4j = new `repositories/neo4j/` package + one line in the factory. | Controllers calling SQL directly: forbidden by the assignment. |
| D4 | An **architecture test** fails if `sqlite3` is imported anywhere outside `models/repositories/sqlite/`, or if a controller imports SQL code. | Turns the assignment's rule into something checked on every test run. | Trusting code review alone. |
| D5 | Domain classes are plain dataclasses; business rules (status transitions, minimum order, totals) live in the model, not in routes. | Rules are tested without Flask or a database; controllers stay thin. | Rules inside route functions. |
| D6 | One `users` table with role `customer` or `admin`; passwords hashed with Werkzeug (ships with Flask); session cookie. Customers register themselves; the admin comes from the seed. | The assignment only asks for basic login. No extra library to learn. | Flask-Login: works, but adds a dependency for little gain at this size. |
| D7 | A small CSRF token (in the session, checked on every POST form). About 15 lines. | Cheap protection against forged form posts. | Flask-WTF: heavier; no CSRF at all: bad habit. |
| D8 | The **cart lives in the session** until the order is submitted. The minimum order is checked on add, on update and again on submit; prices are copied into the order lines at submit. | No half-finished orders in the database; later price changes do not alter submitted orders (same rule as the lab's US-25). | Cart table in the database. |
| D9 | **Images:** upload JPEG/PNG/WebP up to 2 MB, then a preview page, then "Save" or "Discard". The seed script draws simple placeholder pictures with Pillow, so no image files or API keys are needed in the repo. | Meets A2 (preview before saving) with no external service. | The "instruction to an AI image service" path: optional later plan, behind a pluggable `ImageService` with the key only in `.env`. |
| D10 | Order status and payment status exactly as Oblig 4 names them (section 4). | The assessor checks these names. | The lab's longer state machine (company approval, out for delivery). |
| D11 | Allergens: the 14 allergens that must be declared under EU Regulation 1169/2011 (applies in Norway through the EEA). Dietary labels: vegetarian, vegan, gluten-free, lactose-free, halal (the kinds found in the order data). | A fixed, recognised list; the dietary labels are the ones Ekte Mat's customers actually used. | Free-text allergens: cannot be filtered or highlighted. |

## 4. Data model (first version)

| Table | Columns (main) |
|---|---|
| `users` | id, email (unique), name, password_hash, role (`customer` / `admin`), created_at |
| `food_items` | id, name, description, price_nok, min_order_qty, image_path, published, created_at |
| `food_item_events` | food_item_id, event (`corporate_lunch`, `conference`, `julebord`, `wedding`, `confirmation`, `birthday`) |
| `food_item_allergens` | food_item_id, allergen (14 EU codes) |
| `food_item_labels` | food_item_id, label (5 dietary labels) |
| `orders` | id, customer_id, event_date, event_type, guest_count, delivery_address, status, payment_status, submitted_at |
| `order_lines` | id, order_id, food_item_id, quantity, unit_price_nok (frozen at submit) |
| `guest_groups` | id, order_id, description, size, allergy_notes, diet_notes (no guest names: GDPR, lab US-40) |
| `questions` | id, order_id, customer_id, text, asked_at, answer, answered_at, answered_by |

**Order status** (D10): `submitted` → `approved` → `in_preparation` → `delivered`; `submitted` → `rejected`;
`submitted` or `approved` → `cancelled`. Every other change is refused by `order_status.py`.
**Payment status** (independent of order status): `not_paid`, `deposit_paid`, `invoiced`, `paid`.

## 5. Features and their order (each gets its own plan before building)

| Plan | Feature | Requirements | Lab backlog stories |
|---|---|---|---|
| 0 | Walking skeleton: app starts, layers in place, schema, seed, base layout, **log in / log out**, first tests, README, CLAUDE.md | Technical requirements | US-47 (login part) |
| 1 | Admin: food items and images (create, edit, remove, publish, upload with preview) | A1, A2 | US-25, US-02 |
| 2 | Customer: menu by event as cards, cart with minimum order and estimated total | C1, C2 | US-01, US-02 |
| 3 | Register; submit an order with guest groups | C3 | US-47 (registration), US-09, US-40 |
| 4 | My orders (customer); order list with filters and order page (admin) | C4, A3 | US-11, US-17, US-19 |
| 5 | Questions on an order, and answers | C5, A4 | US-21 |
| later | Optional: kitchen view with allergies highlighted, daily capacity check (the order data showed 19 days above capacity), AI image instruction, Norwegian/English | "Going further" | US-22, US-23, US-18 |

**Revision (2026-10-21, before building):** the admin pages in plan 1 need a logged-in admin, but login was first
planned for plan 3. Log in and log out (decision D6) therefore move into plan 0; customer registration stays in plan 3.

## 6. Testing

- **pytest** with Flask's test client and a fresh temporary SQLite database per test.
- Each feature plan lists acceptance tests written from Given/When/Then criteria before the code.
- Always run: model rules (status transitions, minimum order), repositories (round trips), routes
  (happy path + refusals, e.g. a customer opening `/admin` gets 403), and the architecture test (D4).
- Screenshots for the report are taken with Playwright from the seeded app.

## 7. How we work

1. **Plan first.** A larger feature starts as `docs/plans/N - Name-With-Dashes.md`. Code starts only after User1 approves it.
2. **Build on a branch** `feature/N-name` (no spaces in branch names); tests pass before every push.
3. **Review:** User1 reviews the diff on GitHub ("Compare & pull request") and merges it.
4. **After merging**, the plan gets a short "What changed compared with the plan" section.
5. **Never commit** `.env`, API keys or real personal data; only synthetic data.
6. The finished version is tagged `oblig4`. (Created on 2026-10-24 as `Obligatorisk-4`, a GitHub release.)

## 8. Definition of Done (per feature)

- [ ] Acceptance tests from the plan pass, and the whole test suite passes.
- [ ] Works from a clean checkout using only the README commands.
- [ ] No secrets or personal data in the commit.
- [ ] The plan is updated with what changed.
- [ ] Screenshots for the report are captured.

## 9. Risks and open points

- **Group size:** resolved. The group builds several versions of the same assignment with different agents and compares them; this repository is one of them.
- **Repository visibility:** the assignment text says "public, private and shared with the course staff". Plan: private, with the course staff added as collaborators.
- **Windows:** the app must run on User1's Windows machine (Python 3.11 or newer). The README gives Windows commands first.
- **Lab design vs Oblig 4:** the lab domain model is richer (22 classes). This version uses the subset in section 4; the rest stays in `docs/design/` for later.

## 10. What changed compared with the plan (after merging pull request #1)

- **Log in / log out moved into plan 0** (decided before building, see section 5): the admin pages in plan 1 need them.
- **D9 (images):** only the seed's placeholder pictures exist so far; upload with preview is plan 1, as planned.
- **Small additions found while building:** a plain-language 403 message (the default text was technical, seen in the
  browser check); tests no longer write a secret key into `instance/`; the seed script takes the picture folder as a
  parameter so tests do not touch the real `uploads/` folder.
- **D3 (where controllers find the repositories):** not `current_app.repos` as written above, but the helper
  `repos()` in `app/controllers/__init__.py`, which reads `current_app.extensions["repositories"]` (Flask's standard
  place for app-wide objects). Same idea: one factory in `create_app()`, controllers only see `base.py`.
- **Verification:** 22 tests, also from a fresh clone with only the README commands (Python 3.13); every rule test
  was checked by deliberately breaking a copy of the code; the pages were checked in a browser, including phone width.
- Everything else (D1-D11, the data model, the folder layout) was built as planned.
