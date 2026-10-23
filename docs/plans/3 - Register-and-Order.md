# Plan 3: Register and submit an order

- **Status:** Approved by User1 on 2026-10-23 (no changes requested; P3-4, P3-5, P3-7 and P3-10 confirmed). Not built yet.
- **Date:** 2026-10-23
- **Requirements:** C3 ("Log in (or register) and submit the order: event date, number of guests, delivery address,
  and allergy and dietary notes per guest group. No payment solution is needed."). Lab backlog: US-47 (register and
  log in), US-09 (booking request with guest groups), US-40 (allergies per guest group, no guest names), NFR-20 (every
  new order satisfies the validation rules V1-V10 from the lab's order data report).
- **Builds on:** plan 0 (D6 accounts, D8 prices copied at submit, D10 order status, the order tables), plan 2 (the
  cart, which survives log in, P2-9), and plan 6's promise of an `EmailAlreadyUsed` error (P6-7).

## 1. What the customer can do afterwards

1. **Register** with name, e-mail address and password, and be logged in straight away (US-47, criterion 1).
2. From the cart, choose **Send booking request**. A visitor is asked to log in or register first and comes back to
   the order form with the cart unchanged (US-47, criterion 3).
3. Fill in the **order form**: kind of event, event date, number of guests, delivery address, and up to five
   **guest groups**, each with a number of guests and their allergies and dietary needs. There is no field for guest
   names (US-09, US-40).
4. **Submit.** The order is stored with status *Submitted* and payment status *Not paid*, with today's prices
   copied into it; the cart is emptied (US-09, criterion 1; plan 0, D8).
5. See an **order page** straight away, as an on-screen receipt: order number (for example `26-0007`), status, event,
   guests, address, guest groups, the dishes with their prices, and the total.

Staff see the orders in plan 4 (A3).

## 2. Screens

| Screen | URL | Notes |
|---|---|---|
| Register | `/account/register` | Name, e-mail, password twice. Carries `next`, like the log in page. The log in page gets a link "No account? Register". |
| Cart (plan 2) | `/cart` | New button **Send booking request** below the total. |
| Order form | `/account/order` | Log in required. A short summary of the cart at the top (dishes, portions, estimated total), then the form. Errors next to the fields; the form keeps what was typed. |
| Order page | `/account/orders/<id>` | Only for the customer who placed the order. "We have received your booking request" after submitting. Plan 4 adds the list of all your orders. |

## 3. Decisions

| # | Decision | Why | Not chosen |
|---|---|---|---|
| P3-1 | **Registration rules in the model** (`validate_registration` in `domain.py`): name 1-100 characters; an e-mail address with one `@` and a dot after it, at most 254 characters; password at least 10 characters (ASSUMPTION: no source in the data pack) and typed twice. The role is always *customer*, never taken from the form. A taken e-mail address (any upper or lower case) gives "An account with this e-mail address already exists. Log in instead." through `EmailAlreadyUsed` from the repository (plan 6, P6-7). After registering, the customer is logged in (the cart is kept, P2-9) and sent on to `next`. | US-47, criterion 1. One place for the rules, tested without Flask; the repository error keeps the page independent of SQLite or Neo4j. | A confirmation e-mail (US-47) or an e-mail link to verify the address: both need an e-mail service, which Oblig 4 does not have (section 6). |
| P3-2 | **The way in:** "Send booking request" on the cart page leads to `/account/order`, which needs a log in. A visitor goes to the log in page with `next=/account/order`, and the link to the register page keeps that `next`. | US-47, criterion 3: "they are asked to log in or register, and the cart is still there afterwards". | A form that also asks for a new password inside the order form: two jobs in one page. |
| P3-3 | **The order form and its rules** (`validate_order(order, today)` in the model, one rule each from the lab's order data report, see section 4): kind of event required (V4); event date not before today (V9) and at most two years ahead (ASSUMPTION: catches typing mistakes such as 2062); number of guests 1-400 (V5, V6); delivery address as **street, postcode and place**, with the postcode exactly four digits (V10). | US-09 criterion 2 ("nothing is stored and the missing field is highlighted") and NFR-20. Splitting the address is the only way to check the postcode. | One free-text address field: V10 cannot be checked. |
| P3-4 | **Guest groups:** five rows on the form (no JavaScript); empty rows are ignored. A filled row needs a short description (for example "Nut allergy" or "Children") and a number of guests of at least 1; allergies and dietary needs are free text of at most 300 characters each. The groups together may not have more guests than the order (ASSUMPTION: a group lists guests with special needs; everybody else has none). The form says "Do not write guest names". | US-09 criterion 3 ("per guest group with a count ... no field for guest names") and US-40 (health data under GDPR art. 9 is kept per group, not per person). | A name field per guest; one big allergy text for the whole order (the kitchen cannot see how many guests each note concerns). |
| P3-5 | **Every dish must be offered for the chosen kind of event.** If not, the form names the dishes: "Traditional julebord buffet is not offered for Wedding." | Staff decide which events each dish belongs to (US-25, plan 1), and the menu is organised that way (C1). An order for a wedding with the julebord buffet would surprise the kitchen. | Allowing any mix (the event type only as information); limiting the event list to the events all dishes share (hard to explain without JavaScript). |
| P3-6 | **Submitting** re-reads the cart from the repository (as in P2-3). If a dish has left the menu, a line is below its minimum, or the cart is empty, nothing is stored and the customer goes back to the cart or menu with a message (plan 0, D8). Otherwise the order, its lines and its guest groups are stored **in one transaction**: all or nothing. Each line copies today's price per person (V7). There is no total column: the total is always the sum of the lines (V8). Status *submitted*, payment *not_paid* (plan 0, D10). Then the cart is emptied. | Prices frozen in the order (plan 0, D8; lab US-25 criterion 2). A half-stored order would show up in plan 4 with dishes missing. | A typed or stored total (V8: 12 historical totals did not equal guests × price). |
| P3-7 | **One order per click (V1).** The form carries a random hidden key, and `orders.submission_key` is unique in the database. If the same form arrives twice (a double click, or Back and submit again), the repository returns the order that already exists and the customer sees its page. | V1: the old data had 5 orders entered twice. The cart lives in a cookie, so without a key the server cannot tell a double click from a new order. | Disabling the button with JavaScript only: does not work without JavaScript and does not protect the server. |
| P3-8 | **Order number** `YY-NNNN`: the last two digits of the year it was submitted and the order id with four digits (`26-0007`), shown everywhere the customer or staff see the order. Worked out from the id, so it is unique without an extra column (V1). | The same pattern as the old order export (`24-0014`), so staff recognise it. ASSUMPTION: the number does not start at 0001 each year. | A separate counter per year: more code, and two orders could get the same number if it is wrong. |
| P3-9 | **The order page is private:** only the customer who placed the order can open it. Anyone else gets "page not found" (404), so order numbers cannot be guessed to find out that an order exists. Visitors are asked to log in. | Orders hold an address and allergy notes (US-40). | 403: confirms that the order exists. |
| P3-10 | **Only customer accounts can order.** The admin gets "Staff accounts cannot place orders. Log in as a customer." | Keeps staff and customer data apart in the order lists of plan 4. Orders taken by phone (US-20) are a later feature. | Letting the admin order as themselves. |
| P3-11 | **"Today" is the date on the computer that runs the app** (`date.today()`), and the model takes it as a parameter, so tests can choose the date. | Python's time zone for Norway (`ZoneInfo("Europe/Oslo")`) needs an extra package on Windows. ASSUMPTION: the app runs on a computer set to Norwegian time. | A fixed time zone through the `tzdata` package: a new dependency for one line. |

## 4. The order data rules V1-V10 (NFR-20)

From the lab's report `04_Data/04_report_order-data-quality.md` (820 rows of historical orders, 40 with at least one
problem):

| Rule | Problem in the old data | How plan 3 handles it |
|---|---|---|
| V1 | Same order entered twice | Order number from the unique id (P3-8); the same form twice gives one order (P3-7). |
| V2 | Channel spelled in different ways | Not stored yet: every order in this app comes from the website. Phone orders (US-20) are later. |
| V3 | Status typo | The status is set by the app to `submitted`; the database only accepts the six statuses (plan 0, D10). |
| V4 | Event type missing | Required on the form and `NOT NULL` in the database. |
| V5 | Guest count 0 or less | Refused on the form; `CHECK (guest_count > 0)` already in the database. |
| V6 | Guest count above 400 | Refused on the form; `CHECK (guest_count <= 400)` added to the database. |
| V7 | Price per guest 0 | Today's price is copied into each order line; the customer never types a price. |
| V8 | Total does not equal guests × price | No total column; the total is always calculated from the lines. |
| V9 | Event date before the order date | Refused on the form (P3-3). |
| V10 | Postcode not four digits | Separate postcode field, refused unless four digits; also a `CHECK` in the database. |

## 5. Data model change

- `orders`: `delivery_address` is replaced by `delivery_street`, `delivery_postcode` (four digits, `CHECK`) and
  `delivery_city`; new `submission_key TEXT NOT NULL UNIQUE` (P3-7); `guest_count` also gets `<= 400` (V6).
- `order_lines` and `guest_groups` stay as they are (plan 0, section 4).
- `domain.py` gets `Order`, `OrderLine` and `GuestGroup` (the classes plan 0 placed there).
- `repositories/base.py` gets an `OrderRepository` with `add(order)` (one transaction; returns the existing order
  for a known submission key) and `get(order_id)`, plus `EmailAlreadyUsed` (plan 6, P6-7). Plan 4 adds the list
  methods.
- **After pulling, run `python seed.py` once** (it rebuilds the database). Local test data, such as dishes added by
  hand, is lost. The README says so, as after plan 1.
- Plan 6 (Neo4j) models the order with one address property; it is updated when it starts (its section 7 already
  expects the interfaces to grow).

## 6. Files that change

| File | Change |
|---|---|
| `app/models/domain.py` | `Order`, `OrderLine`, `GuestGroup`, `validate_registration`, `validate_order`, `order_number`. |
| `app/models/repositories/base.py` | `OrderRepository`, `EmailAlreadyUsed`. |
| `app/models/repositories/sqlite/` | `orders.py` (new), `users.py` raises `EmailAlreadyUsed`, `schema.sql` (section 5), `__init__.py` adds the order repository. |
| `app/controllers/account.py` | Register, order form, submit and order page. Reads the form, calls the model and the repositories, shows the errors. |
| `app/controllers/shop.py` | Nothing, except what the cart page needs for the new button. |
| `app/views/templates/` | `account/register.html`, `account/order_form.html`, `account/order.html`; a link in `account/login.html`; the button in `shop/cart.html`. |
| `app/views/static/css/style.css` | Order form with guest group rows, order page; phone width. |
| `tests/` | `test_order_rules.py` (rules without Flask), `test_register_and_order.py` (acceptance tests), orders in `test_repositories.py`. |
| `README.md` | "Run `python seed.py` again after pulling plan 3". |
| `docs/screenshots/` | Register, order form (with errors), order page; also at phone width (Oblig 4, section 5.2 asks for the order form). |

## 7. Acceptance tests (written before the code)

**Register (US-47)**
1. Given a visitor, When they register with a name, an e-mail address and the same 10-character password twice,
   Then a *customer* account exists, the password is stored only as a hash, the visitor is logged in and goes to `next`.
2. Given the register form, When the name is empty, the e-mail has no `@`, the password is 9 characters, or the two
   passwords differ, Then each error is shown next to its field, nothing is stored, and the name and e-mail are kept.
3. Given an account for `kari@test.example`, When someone registers `KARI@test.example`, Then it is refused with
   "already exists" and there is still one account.
4. Given a register form with an added field `role=admin` (a tampered form), When it is sent, Then the new account
   is a customer.

**The way in (US-47, criterion 3)**
5. Given a visitor with dishes in the cart, When they choose "Send booking request", Then they are asked to log in;
   When they follow "Register" and register, Then they reach the order form and the cart is unchanged.

**Order form and submitting (C3, US-09, US-40)**
6. Given a logged-in customer with a valid cart, When they submit a valid form with two guest groups, Then one order
   is stored with status *submitted*, payment *not_paid*, today's prices in its lines and both groups; the cart is
   empty; the order page shows the order number, the total and the groups (US-09, criterion 1).
7. Given the order form, When the event type is missing (V4), the date is yesterday (V9) or more than two years ahead,
   the guests are 0 (V5) or 401 (V6), the postcode is `50O7` (V10) or the street is empty, Then each error is shown
   next to its field, nothing is stored and the form keeps what was typed (US-09, criterion 2).
8. Given guest groups, When a row has a number but no description, a number of 0, or the groups add up to more guests
   than the order, Then it is refused; When rows are empty, Then they are ignored. The form has no field for names
   and says "Do not write guest names" (US-09 criterion 3, US-40 criterion 1).
9. Given a dish in the cart that is not offered for the chosen event, When the form is submitted, Then it is refused
   and the dish is named (P3-5).
10. Given a submitted order, When staff change the price of one of its dishes, Then the order still shows the price
    from the moment it was submitted (V7, plan 0 D8).
11. Given a dish that left the menu after it was put in the cart, a line below a raised minimum, or an empty cart,
    When the customer submits, Then no order is stored and they are sent to the cart or menu with a message.
12. Given a submitted form, When exactly the same form is sent again, Then there is still one order and the customer
    sees its page (V1, P3-7).
13. Given an order, When another customer opens its page, Then they get 404; When a visitor opens it, Then they are
    asked to log in.
14. Given a logged-in admin, When they open the order form, Then they are refused with the staff message (P3-10).
15. Given the register or order form sent without a valid CSRF token, When it arrives, Then it is refused (400).

**Model and repository**
16. Given an order whose second line points to a dish id that does not exist, When the repository stores it, Then
    nothing at all is stored (one transaction).
17. Given order 7 submitted in 2026, Then its number is `26-0007`.

## 8. Out of scope (later plans or not in Oblig 4)

- E-mails: the receipt and confirmation e-mails (US-11 criteria 1-2) and the registration e-mail (US-47 criterion 1).
  Oblig 4 has no e-mail service; the order page is the receipt for now.
- The customer's list of orders and the admin's order list and order page (plan 4: C4, A3).
- Changing or cancelling an order (US-12, US-15; the deadline is open question C-02).
- Pick-up or delivery and a delivery time window (US-14, a Should story).
- Deposit for weddings (US-35, open question C-01) and payment (C3: "No payment solution is needed").
- A check against the kitchen's capacity for the date (US-10, US-18, C-09, C-16).
- Showing allergy notes only to some staff roles, and logging who read them (US-40 criterion 2, NFR-06): Oblig 4 has
  one staff role.
- Forgotten password, changing the password, and deleting the account (US-41).

## 9. Risks and open points

- **Free text can still hold names.** "Ola is allergic to nuts" in a notes field is health data about a named person.
  The form asks for no names (P3-4); the kitchen view later could warn about capital letters. ASSUMPTION: the hint is
  enough for Oblig 4.
- **Registration tells whether an e-mail address has an account** (the log in page does not, US-47 criterion 2).
  A safer flow needs e-mail (section 8). Accepted for now.
- **Guests and portions are independent.** A buffet for 50 guests can be ordered with 30 portions. ASSUMPTION: the
  customer decides; Ekte Mat checks when it approves the order. A question for the product owner.
- **400 guests is a per-order limit (V6),** not a daily kitchen limit: the old data had 19 days above the stated
  capacity (C-16). The daily check is out of scope.
- **The database must be rebuilt** (section 5). Teammates who pull must run `python seed.py` once.
- **The date comes from the computer's clock** (P3-11). On a server in another time zone, "today" could be wrong for
  a few hours around midnight.

## 10. Done when

- [ ] Acceptance tests 1-17 pass, plus all earlier tests.
- [ ] Every rule test has been seen to fail when its rule is broken on purpose (as in plans 1 and 2).
- [ ] Works from a fresh clone with the README commands, and on User1's Windows PC.
- [ ] Checked in a browser at 1200 px and 390 px (page width measured on every page); screenshots of the register page,
      the order form with errors and the order page saved in `docs/screenshots/`.
- [ ] This plan gets a "What changed compared with the plan" section.
