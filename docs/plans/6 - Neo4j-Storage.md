# Plan 6: Neo4j storage

- **Status:** Draft, awaiting Rave's approval.
- **Date:** 2026-10-21
- **Requirements:** Oblig 5: all application data is stored in Neo4j. The assignment text is not in the repository yet;
  this plan is checked against it as soon as it is published (section 7).
- **Builds on:** plan 0 (D2, D3, D4: repositories behind `base.py`, one composition root, architecture test) and every
  feature plan before it. Built **after** plans 2-5 and the `oblig4` tag, so that the Oblig 4 version stays on SQLite.

## 1. What is different afterwards

1. The running application keeps users, food items, orders, guest groups and questions in a **Neo4j graph**
   (Neo4j Aura for the shared instance). No page, route or template changes: customers and staff see the same site.
2. The data is modelled as a graph, not as tables copied into nodes: dishes are linked to the events, allergens and
   dietary labels they belong to, and orders are linked to the customer, the event and the dishes they include.
3. `python seed.py` fills Neo4j with the same synthetic data as today.
4. The tests check both storages with the same repository tests, so we can show that the two behave the same.

## 2. Graph model

```
(:User)-[:PLACED]->(:Order)-[:FOR_EVENT]->(:Event)<-[:OFFERED_FOR]-(:FoodItem)
                    (:Order)-[:INCLUDES {quantity, unit_price_nok}]->(:FoodItem)
                    (:Order)-[:HAS_GROUP]->(:GuestGroup)
                                                       (:FoodItem)-[:CONTAINS]->(:Allergen)
                                                       (:FoodItem)-[:HAS_LABEL]->(:DietaryLabel)
(:User)-[:ASKED]->(:Question)-[:ABOUT]->(:Order)
(:User)-[:ANSWERED]->(:Question)
```

| Plan 0 table (section 4) | In the graph |
|---|---|
| `users` | `(:User {id, email, name, password_hash, role, created_at})` |
| `food_items` | `(:FoodItem {id, name, description, price_nok, min_order_qty, image_path, no_allergens, published, created_at})` |
| `food_item_events`, `food_item_allergens`, `food_item_labels` | Relationships `OFFERED_FOR`, `CONTAINS`, `HAS_LABEL` to **shared** code nodes `(:Event {code, name})`, `(:Allergen {code, name})`, `(:DietaryLabel {code, name})` |
| `orders` | `(:Order {id, event_date, guest_count, delivery_address, status, payment_status, submitted_at})`; customer as `PLACED`, event type as `FOR_EVENT` |
| `order_lines` | Relationship `(:Order)-[:INCLUDES {quantity, unit_price_nok}]->(:FoodItem)` |
| `guest_groups` | `(:GuestGroup {id, description, size, allergy_notes, diet_notes})` with `HAS_GROUP` (still no guest names: lab US-40) |
| `questions` | `(:Question {id, text, asked_at, answer, answered_at})` with `ASKED`, `ABOUT` and `ANSWERED` |

The code nodes are created from the dictionaries in `app/models/domain.py` (`EVENTS`, `ALLERGENS`, `DIETARY_LABELS`),
so the model stays the single list of allowed codes.

## 3. Decisions

| # | Decision | Why | Alternative not chosen |
|---|---|---|---|
| P6-1 | The app connects with the **official `neo4j` Python driver** over Bolt (`neo4j+s://<id>.databases.neo4j.io`), with `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD` and `NEO4J_DATABASE` as environment variables. The Claude Code MCP connector (`.mcp.json`) is only a development tool and is not used by the app. | The driver is Neo4j's supported way for Python programs; the password stays in each person's environment and the team's password manager, never in Git. | Calling the HTTP Query API by hand: more code, no connection pooling or retries. |
| P6-2 | **A second implementation next to SQLite:** new package `app/models/repositories/neo4j/` implementing every interface in `base.py`. `create_app()` picks it from the setting `STORAGE` (`neo4j` or `sqlite`, default `neo4j`). If `STORAGE=neo4j` and a `NEO4J_*` variable is missing, the app stops with a message naming the missing variables (never their values). | Exactly what plan 0 (D3) prepared: controllers and views do not change. Keeping SQLite lets the same tests run on both, and lets anyone run the app without a Neo4j account. | Deleting the SQLite package: less code, but nothing to compare against and no offline fallback. Rave decides if the assignment asks for SQLite to be removed (section 7). |
| P6-3 | **Events, allergens and dietary labels are shared nodes**, linked by relationships, not list properties on the dish. `initialise()` creates the code nodes with `MERGE`. | This is what makes it a graph: questions like "published dishes for a wedding that contain no milk" become one short pattern, and the report can show it. | Lists as properties on `FoodItem`: simplest translation of today's code, but it is just a table stored in a graph database. |
| P6-4 | **Order lines are relationships** `INCLUDES {quantity, unit_price_nok}` between the order and the dish. `is_ordered(id)` becomes "does any `INCLUDES` point to this dish?", and `delete()` refuses such a dish instead of using `DETACH DELETE`, which would silently remove the order lines. | An order line has no life of its own; the frozen price (plan 0, D8) fits as a property of the link. The delete guard does what SQLite's foreign key on `order_lines` does today. | An `OrderLine` node: needed only if a line gets its own id or relationships, which no plan asks for. |
| P6-5 | **Ids stay whole numbers.** A `(:Sequence {name, value})` node per kind is increased in the same transaction that creates the node; ids are never reused. | Routes (`/admin/items/<int:id>`), the domain classes (`id: int`) and the tests stay unchanged. | Neo4j's internal `elementId()`: may be reused after a delete and is a long string. UUIDs: change every route and test. |
| P6-6 | **Constraints in `initialise()`:** unique `User.email`; unique `id` for every node kind; unique `code` for the code nodes. All created with `IF NOT EXISTS`, so running it twice is safe. Rules on values (price 0-100 000, minimum order 1-1000, known codes) stay in the model (P1-1). | Neo4j has no CHECK constraints like SQLite; the model already validates every form before saving, so that rule stays in one place. | Property type and existence constraints: depend on the Neo4j edition; we do not rely on them (section 7). |
| P6-7 | **Storage-neutral errors:** `base.py` gets `EmailAlreadyUsed`. Both implementations raise it for a duplicate e-mail (SQLite turns `IntegrityError` into it; Neo4j turns its constraint error into it). | The tests and, from plan 3, the registration page must not know which database is used. Today `tests/test_repositories.py` imports `sqlite3` for this. | Letting each database's own error reach the caller: breaks D3. |
| P6-8 | **One driver per application**, created in `create_app()` and closed when the app stops; **one managed transaction per repository call** (`execute_read` / `execute_write`, which retry on short network errors). Each list page is **one** Cypher query that also collects the linked codes. | Same pattern as the SQLite package (one short-lived connection per operation); one query per page avoids many round trips to Aura in the cloud. | A session per request: more to keep track of in Flask, no gain at this size. |
| P6-9 | **Dates as Neo4j `date` / `datetime` values**, converted to and from Python in the repository; shown as YYYY-MM-DD as before. | Dates can be compared and sorted in Cypher (order filters in plan 4). | ISO text, as in SQLite: works, but loses date comparisons in the database. |
| P6-10 | **Pictures stay files** in `app/views/static/uploads/`; the `FoodItem` node keeps `image_path`. | A database is the wrong place for picture files, and Aura Free has little storage. Plan 1's `ImageStore` is unchanged. | Pictures as bytes in Neo4j. |
| P6-11 | **Tests:** the repository tests run on **both** storages (a parametrised pytest fixture). The Neo4j run uses a **local, throw-away Neo4j in Docker**, found through `NEO4J_TEST_URI`, and is skipped with a clear message when it is not set. The whole suite can also be run on Neo4j with `TEST_STORAGE=neo4j`. Tests **never** use the Aura instance. | `reset()` deletes everything, so tests must not touch the instance we demo from. Docker is already installed on the development machine; Neo4j Desktop works too. | Testing against Aura: wipes shared data and is slow. Mocking the driver: does not prove the Cypher is right. |
| P6-12 | **`seed.py` asks before deleting:** it prints the storage and the address it is about to empty (never the password) and continues only after "yes", or with `--yes`. | On SQLite a mistake costs a local file; on Neo4j it empties the shared instance. | No confirmation, as today. |
| P6-13 | **Architecture test extended:** the `neo4j` driver may only be imported in `app/models/repositories/neo4j/`, `sqlite3` only in the SQLite package, and controllers import neither implementation. The check looks at absolute imports of the driver, so our own package name `neo4j` in `create_app()` does not count. | Keeps plan 0's rule (D4) true for both storages, checked on every run. | Trusting review. |
| P6-14 | **No data migration.** The Neo4j database is filled by `seed.py`; there is only synthetic data to move. | Nothing real to keep; a migration script would be code that runs once. | A SQLite-to-Neo4j export script. |

## 4. Files that change

| File | Change |
|---|---|
| `requirements.txt` | Add the official `neo4j` driver (exact version pinned when building). |
| `app/models/repositories/base.py` | `EmailAlreadyUsed`; docstrings say "storage", not "SQLite". |
| `app/models/repositories/neo4j/` | New: `__init__.py` (`Neo4jRepositories`: driver, constraints, code nodes, `reset()`), one file per repository (`users.py`, `food_items.py`, and the order and question repositories from plans 3-5). |
| `app/models/repositories/sqlite/` | Raise `EmailAlreadyUsed` for a duplicate e-mail. Nothing else. |
| `app/__init__.py` | Choose the storage from `STORAGE`; check the `NEO4J_*` variables; close the driver when the app stops. |
| `seed.py` | Confirmation before deleting (P6-12). |
| `tests/` | Storage fixture for both implementations; `test_repositories.py` without `sqlite3`; the CHECK-constraint test marked as SQLite-only; new graph tests (section 5); architecture test (P6-13). |
| `.env.example`, `README.md`, `CLAUDE.md` | `STORAGE`, the four `NEO4J_*` variables, `NEO4J_TEST_URI`; the Docker command for the test database; the layout line about storage. |
| `docs/design/` | A graph model diagram (section 2) for the report. |

## 5. Acceptance tests (written before the code)

**Starting and settings**
1. Given `STORAGE=neo4j` and all `NEO4J_*` variables, When the app starts twice, Then the constraints and the code
   nodes exist once, and no data is deleted.
2. Given `STORAGE=neo4j` and no `NEO4J_PASSWORD`, When the app starts, Then it stops with a message naming the
   missing variable, and no secret is printed.
3. Given `STORAGE=sqlite`, When the app starts, Then it works as in Oblig 4 without any Neo4j settings.

**Same behaviour on both storages** (every test in `test_repositories.py`, run once per storage)
4. A user is found by e-mail regardless of case; a second user with the same e-mail raises `EmailAlreadyUsed`.
5. A food item round trip keeps events, allergens and labels, sorted.
6. `list(published_only=True)` returns only published items, ordered by name.
7. `update()` replaces the lists: an allergen removed in the form is no longer linked.
8. `delete()` removes the item; two new items get different whole-number ids, and a deleted id is not given out again.
9. `is_ordered()` is true once an order includes the item (plan 1, P1-6); calling `delete()` on it anyway raises
   an error and leaves both the item and the order line in place.

**Graph model** (Neo4j only)
10. Given two dishes that both contain milk, When they are saved, Then there is one `(:Allergen {code: "milk"})`
    with two `CONTAINS` relationships.
11. Given a dish, When it is deleted, Then the shared code nodes are still there.
12. Given a submitted order (plan 3), Then the graph has `(:User)-[:PLACED]->(:Order)-[:INCLUDES]->(:FoodItem)` with
    the quantity and the frozen unit price on `INCLUDES`.

**Safety and architecture**
13. Given `seed.py` without `--yes`, When the answer is not "yes", Then nothing is deleted.
14. The architecture test fails if the `neo4j` driver is imported outside its package or a controller imports
    either storage.
15. The whole suite passes with `TEST_STORAGE=neo4j` against the Docker database, and with the default SQLite run.

**By hand**
16. With the seeded Aura instance: browse the menu, add and edit a dish as admin, submit an order, and check in
    Neo4j Browser (or with Claude Code's read-only Cypher tool) that the nodes and relationships match section 2.
    Screenshots of the graph go in the report.

## 6. Out of scope (later plans)

- Using the graph for new features, such as recommending dishes or a kitchen view of all allergies for a day
  (plan 0, "later"). The model in section 2 makes these possible.
- Keeping the cart in Neo4j: it stays in the session until the order is submitted (plan 0, D8).
- Separate Aura instances for test and production.
- Moving existing SQLite data (P6-14).

## 7. Risks and open points

- **The Oblig 5 text is not out yet.** If it asks for something else (for example removing SQLite, or a given
  model), this plan is changed and approved again before any code.
- **Interfaces grow before this is built.** Plans 2-5 add order and question repositories to `base.py`. The graph
  model already covers their tables (section 2); the exact method list is checked when this plan starts.
- **AuraDB Free limits:** the instance pauses after some days without use and has a cap on nodes and relationships.
  Check the numbers in the Aura console; resume the instance before demos and assessment.
- **Who can reach the Aura instance:** it is in one team member's Aura account. Everyone who runs the app against it
  needs the database password from the password manager; the seed (P6-12) is run only after agreeing in the team.
- **Constraint features:** uniqueness constraints work on every Neo4j edition. Type and existence constraints may not
  be available on AuraDB Free or Community, so the plan does not depend on them (P6-6).
- **Speed:** every query goes to Aura over the internet. P6-8 keeps it to one query per page; check that pages still
  feel instant in the browser check.

## 8. Done when

- [ ] Acceptance tests 1-15 pass (4-9 and 15 on both SQLite and Neo4j in Docker), plus all earlier tests.
- [ ] Works from a fresh clone with the README commands, with `STORAGE=neo4j` against Aura and with `STORAGE=sqlite`.
- [ ] Checked in a browser against the seeded Aura instance (test 16), including phone width; graph screenshots
      saved for the report.
- [ ] No password, URI with credentials or `.env` in the commit.
- [ ] This plan gets a "What changed compared with the plan" section after merging.
