# Plan 4: My orders, and orders in the admin panel

- **Status:** Approved by User1 on 2026-10-23 (no changes requested). Not built yet.
- **Date:** 2026-10-23
- **Requirements:** C4 ("The customer's own orders with their current status ... and payment status") and A3 ("A list
  of all customer orders that can be filtered by status and event date, and a page per order to manage it: order
  status (submitted → approved → in preparation → delivered, or rejected/cancelled) and payment status (e.g. not
  paid, deposit paid, invoiced, paid)"). Lab backlog: US-11 criterion 3 (My orders), US-17 (one list with status and
  time received; highlight after 24 hours; filters), US-19 (approve or reject with one action; a reason when
  rejecting), NFR-19 (store the time of the first reply; share answered within 24 hours per month), NFR-05 (target:
  95 % within 24 hours).
- **Design used:** the lab's order state machine (`docs/design/02_uml_state-order.*`), simplified in plan 0 (D10).
- **Builds on:** plan 0 (D10 statuses, `order_status.py` reserved for the state machine), plan 1 (admin panel, the
  automatic test of every admin route), plan 3 (orders, the order page, `STATUS_NAMES` and `PAYMENT_NAMES`).

## 1. What changes afterwards

**For customers (C4)**
1. **My orders** (a header link for logged-in customers): every order of theirs, newest first, with order number,
   event, event date, status, payment status and total. Each row opens the order page from plan 3 (US-11, criterion 3).
2. The order page shows the current status in words, and the **reason** if Ekte Mat rejected or cancelled the order.

**For staff (A3)**
3. **Orders** in the admin panel: all orders in a table with order number, time received, event date, event,
   customer, guests, total, status and payment status (US-17, criterion 1).
4. **Filters** by status (links with a count, for example "Submitted (3)") and by event date (from and to), alone or
   together (A3; US-17, criterion 3).
5. Orders still *Submitted* more than **24 hours** after they arrived are highlighted (US-17, criterion 2).
6. **An order page for staff:** everything the customer sent, including the guest groups' allergy notes and the
   customer's name and e-mail, and one button for each status change that is allowed now, for example **Approve**,
   **Reject**, **Cancel** (US-19: "with one action"). Rejecting or cancelling asks for a reason.
7. **Payment status** is set on the same page: not paid, deposit paid, invoiced or paid.
8. The admin dashboard shows how many orders wait for a reply and, per month, **how many were answered within
   24 hours** (NFR-19).

## 2. Screens

| Screen | URL | Notes |
|---|---|---|
| My orders | `/account/orders` | Log in required. Empty list: a link to the menu. |
| Order page (plan 3) | `/account/orders/<id>` | Adds the reason for a rejection or cancellation. |
| Orders (admin) | `/admin/orders`, `?status=submitted`, `?date_from=2026-11-01&date_to=2026-11-30` | Status links above the table; a small date form (GET). |
| Order page (admin) | `/admin/orders/<id>` | Details, status buttons, payment form. |
| Admin dashboard (plan 0) | `/admin/` | New: orders waiting for a reply, and the reply-time table. |

Every status and payment change is a POST form with the CSRF token (team rule).

## 3. Decisions

| # | Decision | Why | Not chosen |
|---|---|---|---|
| P4-1 | **The state machine lives in the model**, in `app/models/order_status.py` (the file plan 0 reserved): `submitted → approved, rejected or cancelled`; `approved → in_preparation or cancelled`; `in_preparation → delivered`; `delivered`, `rejected` and `cancelled` are final. One function, `change_status(order, new_status, now, reason)`, refuses everything else. The staff page shows a button only for the changes allowed now. | A3 lists these statuses; the lab's state machine has the same core, and plan 0 (D10) chose the simpler names. One place for the rule; the database already refuses unknown statuses (plan 0). | Rules in the route; letting staff pick any status from a list (the lab data had a status typo, V3, and "jumps" are just as wrong). |
| P4-2 | **Rejecting or cancelling needs a reason** (1-300 characters), stored with the order and shown to the customer on the order page and in My orders. | US-19 criterion 2: "a reason is required and sent to the customer". There is no e-mail service (plan 3, section 8), so the order page is where the customer sees it. ASSUMPTION: a cancellation by staff also needs a reason, for the same reason. | A reason only for rejections. |
| P4-3 | **First reply time (NFR-19):** the first time an order leaves *Submitted* (approved, rejected or cancelled), the time is stored in `first_replied_at` and never changed again. The dashboard shows, per month in which orders arrived, how many were answered within 24 hours, how many later, and how many still wait; the list highlights *Submitted* orders older than 24 hours. | NFR-19 is the only way to check NFR-05 (95 % within 24 hours); the lab data shows 57.8 % waited longer in peak months. ASSUMPTION: a reply is the first status change by staff, and 24 hours means 24 clock hours, nights and weekends included (NFR-05 does not mention working hours). | Counting working hours only (no source); no measurement (NFR-05 could never be checked). |
| P4-4 | **A change is saved only if the order still has the status the page showed.** The form sends the status it was built from; the repository updates `WHERE status = <that status>`. If someone else changed the order in the meantime, nothing happens and the page says so. | Two staff members, or one with two browser tabs, could otherwise approve and reject the same order, or a stale page could jump over a status. | Last change wins without a warning. |
| P4-5 | **Payment status is independent of the order status** and can be set to any of its four values. | Plan 0 keeps the two apart, and staff need to correct mistakes. Deposits (US-35) and invoices (US-36) have their own rules later. ASSUMPTION: no payment rules in Oblig 4. | Payment rules tied to statuses now. |
| P4-6 | **The staff list is sorted by event date, soonest first** (then by order number). Filters are query parameters (`status`, `date_from`, `date_to`; both dates included). An **unknown status answers 404**; an impossible date, or a "from" date after the "to" date, gives a message and **no rows**, never the unfiltered list. | The kitchen and the coordinator work towards event dates. Same principle as the menu filters (plan 2, P2-6): a mistyped filter must not look like a filtered list. | Newest first (puts next week's events at the bottom); ignoring a bad filter. |
| P4-7 | **The staff order page shows the allergy notes** of every guest group, with the customer's name and e-mail address. | The coordinator needs them to judge the order, and in the lab state machine the kitchen confirms the allergies before preparation starts (US-23). Oblig 4 has one staff role, so hiding notes from some staff (US-40 criterion 2, NFR-06) is out of scope. | Hiding allergy notes from the admin. |
| P4-8 | **My orders is newest first,** by the time the order was sent; it shows only the logged-in customer's orders. The header gets "My orders" for customers. Order pages stay private (plan 3, P3-9). | A customer usually looks for the order they just sent. | Sorting by event date. |
| P4-9 | **The seed adds sample orders** for the two test customers, in every status and with different payment statuses, and with event dates counted from the day the seed runs (so they are never in the past). One *Submitted* order "arrived" 30 hours earlier, to show the highlight. Every sample order passes the plan 3 rules. | Lists, filters, the dashboard and the report's screenshots need data; synthetic data only (team rule). | An empty order list after seeding. |
| P4-10 | **New columns are added on start:** `initialise()` adds `status_reason` and `first_replied_at` to an existing `orders` table if they are missing (`ALTER TABLE ... ADD COLUMN`). Existing orders are kept; running `python seed.py` is only needed to get the sample orders. | Plans 1 and 3 made everyone rebuild their database and lose test data. Adding columns is safe in SQLite; it is a few lines inside the SQLite package only. | "Run the seed again" a third time. |

## 4. Files that change

| File | Change |
|---|---|
| `app/models/order_status.py` (new) | `ALLOWED`, `next_statuses(status)`, `change_status(...)`, `StatusError` (P4-1 to P4-3). |
| `app/models/domain.py` | `Order` gets `status_reason`, `first_replied_at`, and `customer_name` / `customer_email` (filled when staff load orders); `reply_stats(orders)` for the dashboard (P4-3). |
| `app/models/repositories/base.py` | `OrderRepository`: `list(status, date_from, date_to)`, `list_for_customer(customer_id)`, `update_status(order, expected_status)`, `update_payment_status(order_id, payment_status)`. |
| `app/models/repositories/sqlite/` | `orders.py` (the new methods, P4-4), `schema.sql` (two columns), `__init__.py` (P4-10). |
| `app/controllers/account.py` | My orders. |
| `app/controllers/admin.py` | Order list with filters, order page, status and payment forms; the dashboard numbers. |
| `app/views/templates/` | `account/my_orders.html`, `admin/orders.html`, `admin/order.html`; the reason on `account/order.html`; the dashboard; "My orders" in `base.html`. |
| `seed.py` | Sample orders (P4-9). |
| `tests/` | `test_order_status.py` (state machine and reply statistics without Flask), `test_orders_pages.py` (acceptance tests), orders in `test_repositories.py`; the every-admin-route test in `test_admin_items.py` also fills in order ids (today it only fills in `<int:item_id>`, so new order pages would answer 404 and not be checked). |
| `docs/` | Screenshots of My orders, the order list and the staff order page (Oblig 4, section 5.2); `report-notes.md`; plan 3's Windows box ticked. |

## 5. Acceptance tests (written before the code)

**C4, My orders**
1. Given a customer with two orders and another customer with one, When the first customer opens My orders, Then
   exactly their two orders are shown, newest first, each with number, event, event date, status, payment status and
   total (C4; US-11, criterion 3).
2. Given a visitor, When they open My orders, Then they are asked to log in.
3. Given staff reject an order with a reason, When the customer opens My orders and the order page, Then both show
   *Rejected*, and the order page shows the reason (US-19, criterion 2).

**A3, the order list**
4. Given orders from two customers, When the admin opens Orders, Then every order is listed with number, time
   received, event date, customer, status, payment status and total, sorted by event date (US-17, criterion 1).
5. Given orders in several statuses, When the admin chooses "Submitted", Then only submitted orders are shown, and
   each status link shows its count; an unknown status answers 404.
6. Given orders on several dates, When the admin filters from one date to another, Then only orders with an event
   date in that range (both days included) are shown, also together with a status; a "from" date after the "to"
   date, or an impossible date, gives a message and no rows (P4-6).
7. Given a submitted order that arrived 25 hours ago and one that arrived an hour ago, When the list is shown, Then
   only the first is highlighted; an approved order is never highlighted (US-17, criterion 2).

**A3, the staff order page**
8. Given an order with guest groups, When the admin opens its page, Then it shows the customer's name and e-mail,
   every group with its allergy and diet notes, the lines with their stored prices, and the total.
9. Given an order in each status, When the admin opens its page, Then exactly the allowed changes are offered:
   Submitted → Approve, Reject, Cancel; Approved → In preparation, Cancel; In preparation → Delivered; none for
   Delivered, Rejected and Cancelled (P4-1).
10. Given a submitted order, When the admin approves it, Then it is *Approved* and its first reply time is stored;
    When it later moves to *In preparation*, Then the first reply time does not change (NFR-19).
11. Given a submitted order, When the admin rejects it without a reason, Then nothing changes and a message asks for
    one; with a reason, Then it is *Rejected* and the reason is stored (US-19, criterion 2).
12. Given a delivered order, When a form asks to set it back to *Submitted* (a tampered form), or a submitted order
    is sent straight to *Delivered*, Then it is refused and nothing changes (P4-1).
13. Given a page that still shows *Submitted*, When the order was approved in another tab and the admin now rejects
    it from the old page, Then nothing changes and the page says the order was changed in the meantime (P4-4).
14. Given an order, When the admin sets each of the four payment statuses, Then each is stored; an unknown payment
    status is refused (P4-5).
15. Given a customer or a visitor, When they open or post to any `/admin/orders` page, Then they get 403 or are sent
    to log in, and nothing changes (the automatic every-admin-route test, now with order ids).

**Measurement, seed and database**
16. Given orders that arrived in October (answered after 10 hours, after 30 hours, not yet) and one in November
    (answered after 2 hours), When the reply statistics are made, Then October shows 1 of 3 within 24 hours, 1 later
    and 1 waiting, and November 1 of 1 (NFR-19; model test).
17. Given `python seed.py`, Then there are sample orders in all six statuses, none with an event date in the past,
    and every one passes the plan 3 order rules.
18. Given a database from plan 3 (without the two new columns) with an order in it, When the app starts, Then the
    columns exist and the order is still there (P4-10).

## 6. Out of scope (later plans or not in Oblig 4)

- E-mails to the customer on approval or rejection (US-19 criterion 1, US-11 criterion 2): the status and reason on
  the order page replace them for now.
- The lab state machine's extra states: awaiting company approval (US-31), out for delivery (US-29) and invoiced as
  an order status (US-36, US-37). Oblig 4 uses the statuses in A3 (plan 0, D10).
- The guards in the lab state machine: a capacity check before approving (US-18) and the kitchen's allergy
  confirmation before preparation (US-23).
- A history of every change with user and time (US-12 criterion 3, NFR-06), and changes to an order's dishes,
  guests or address by staff or customers (US-12).
- Customers cancelling themselves (US-15), deposits (US-35), invoices through Fiken (US-36).
- Questions on an order (plan 5: C5, A4).

## 7. Risks and open points

- **The 24-hour count includes nights and weekends** (P4-3). If Ekte Mat counts working hours, the numbers will look
  worse than they are. A question for the product owner, together with peak months (C-18).
- **"First reply" is the first status change.** A phone call to the customer does not count; staff must use the
  system for the number to be true.
- **Adding columns on start** (P4-10) only covers new columns. A change to an existing column would still need the
  seed, as in plans 1 and 3.
- **The seed's dates move with the day it runs,** so screenshots taken on different days show different dates.
- **Plan 6 (Neo4j)** must implement the new repository methods and the "only if the status is still X" update; its
  section 7 already expects the interfaces to grow.

## 8. Done when

- [ ] Acceptance tests 1-18 pass, plus all earlier tests.
- [ ] Every rule test has been seen to fail when its rule is broken on purpose (as in plans 1-3).
- [ ] Works from a fresh clone with the README commands, and on User1's Windows PC.
- [ ] Checked in a browser at 1200 px and 390 px (page width measured on every page); screenshots of My orders, the
      order list (with a filter) and the staff order page saved in `docs/screenshots/`.
- [ ] `docs/report-notes.md` updated, and this plan gets a "What changed compared with the plan" section.
