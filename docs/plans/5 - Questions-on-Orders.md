# Plan 5: Questions on an order

- **Status:** Done. Approved by User1 on 2026-10-24 (no changes requested); built in pull request #18, merged by
  User1 on 2026-10-24.
- **Date:** 2026-10-24
- **Requirements:** C5 ("Ask a question about a specific order and read Ekte Mat's answer") and A4 ("Read and answer
  customers' questions about their orders"). Lab backlog: US-21 (the coordinator reads and answers questions inside
  the system "so that the whole conversation is kept with the order instead of in e-mail threads"; criterion 1: the
  question is shown on the order page; criterion 2: the customer sees the answer under My orders). Source of US-21:
  the IT landscape, "No customer database; customer details only in e-mail threads".
- **Builds on:** plan 0 (the `questions` table and the `Question` class it reserved), plan 3 (the customer's order
  page, private to its customer), plan 4 (My orders, the staff order page, "save only if it is still ..." from P4-4).
- **After this plan:** all of C1-C5 and A1-A4 exist, so the version to assess gets the tag `Obligatorisk-4` (plan 0,
  section 7).

## 1. What changes afterwards

**For customers (C5)**
1. The order page has a **Questions** section: every question about this order with Ekte Mat's answer (or "waiting
   for an answer"), oldest first, and a box to ask a new one.
2. **My orders** shows, per order, how many questions are answered and how many wait (US-21, criterion 2).

**For staff (A4)**
3. **Admin → Questions:** the questions that wait for an answer, the one that has waited longest at the top, with the
   order number, the customer and how long it has waited. Links to show answered questions, or all.
4. The **staff order page** shows the order's questions, each unanswered one with a box to answer it (US-21,
   criterion 1).
5. The admin dashboard shows how many questions wait for an answer.

## 2. Screens

| Screen | URL | Notes |
|---|---|---|
| Order page (customer, plan 3) | `/account/orders/<id>` | New section "Questions"; the form posts to `/account/orders/<id>/questions`. |
| My orders (plan 4) | `/account/orders` | New column "Questions", for example "1 answered · 1 waiting". |
| Questions (admin) | `/admin/questions`, `?show=answered`, `?show=all` | Default: waiting for an answer. |
| Order page (staff, plan 4) | `/admin/orders/<id>` | New section "Questions" with an answer form per unanswered question; posts to `/admin/questions/<id>/answer`. |
| Admin dashboard | `/admin/` | New number: questions waiting for an answer. |

## 3. Decisions

| # | Decision | Why | Not chosen |
|---|---|---|---|
| P5-1 | **One question, one answer**, as in the table from plan 0 (`text`, `answer`, `answered_at`, `answered_by`). A follow-up is a new question. On the order page the questions and answers read as one conversation, oldest first. | US-21 asks for the conversation to be kept with the order; the table already exists, so **no database change**. | A message thread where both sides write freely: a new table and more rules for little gain in Oblig 4. |
| P5-2 | **Questions live on the order pages**, not on a page of their own for customers; staff also get one list of all questions. | US-21 criterion 1 ("shown on the order page"); a question only makes sense next to the order it is about. Staff need the list to see what waits, across all orders. | A general contact form not tied to an order (not C5). |
| P5-3 | **Rules in the model** (`domain.py`): a question is 1-1000 characters and an answer 1-2000, spaces at the ends removed (ASSUMPTION: no source gives a length). The form says "Do not write guest names". | One place for the rules; the hint follows US-40 and the plan 3 order form, since customers will write about allergies. | No limit: a page could be flooded with one giant text. |
| P5-4 | **Who may do what:** only the customer who placed the order asks questions about it (anyone else gets 404, like the order page, P3-9); only staff answer; staff do not ask and customers do not answer. | Orders and their questions can hold health data (allergies, US-40). | Letting staff write questions "on behalf of" a customer who phoned (not asked for in C5 or A4). |
| P5-5 | **A question is answered once, and the answer is saved only if it is still unanswered** (`WHERE answer IS NULL`), the same pattern as P4-4. A second answer from another tab or another staff member is refused with a message. | Two staff members could otherwise overwrite each other's answer without knowing. Correcting an answer: a new answer to a follow-up question (ASSUMPTION). | Editing answers afterwards; last answer wins. |
| P5-6 | **Questions on orders in every status**, also delivered, rejected and cancelled ones. | Customers ask about invoices after delivery and about the reason for a rejection (ASSUMPTION). | Only open orders. |
| P5-7 | **The staff list: oldest waiting question first.** `?show=waiting` (default), `answered` or `all`; anything else answers 404 (as P2-6 and P4-6). Each row shows how long the question has waited. | The question that has waited longest is the most urgent (the lost-request problem behind US-17 applies to questions too). | Newest first. |
| P5-8 | **Orders are loaded with their questions** (the repository adds them, like lines and groups), so My orders and both order pages need no extra calls. Staff lists of questions come from a `QuestionRepository` that also gives the order number and the customer's name. | Keeps the controllers thin (team rule) and the number of database queries per page fixed. | Counting questions in the controller. |
| P5-9 | **The customer sees "Ekte Mat" as the one who answered**, not the staff member's name; staff see who answered. | Ekte Mat answers as a company; staff names stay internal. | Showing the staff member's name to customers. |
| P5-10 | **The seed adds sample questions** on the sample orders: some answered, some waiting. | The new pages and the screenshots for the report need data. | Empty question lists after seeding. |

## 4. Files that change

| File | Change |
|---|---|
| `app/models/domain.py` | `Question` (plan 0 reserved it), `validate_question`, `answer_question` (P5-3, P5-5); `Order.questions`. |
| `app/models/repositories/base.py` | `QuestionRepository`: `add`, `list(show)`, `get`, `save_answer(question)` (only if still unanswered). |
| `app/models/repositories/sqlite/` | `questions.py` (new); `orders.py` loads each order's questions; `__init__.py` adds the repository. No schema change. |
| `app/controllers/account.py` | Asking a question. |
| `app/controllers/admin.py` | The questions list, answering, the dashboard number. |
| `app/views/templates/` | The questions section on `account/order.html` and `admin/order.html`; a column in `account/my_orders.html`; `admin/questions.html` (new); the dashboard. |
| `seed.py` | Sample questions (P5-10). |
| `tests/` | `test_questions.py` (acceptance tests and the rules); questions in `test_repositories.py`; the every-admin-route test also fills in question ids. |
| `docs/` | Screenshots of the questions on the customer's order page and in the admin panel (Oblig 4, section 5.2); `report-notes.md`; plan 4's Windows box ticked. |

## 5. Acceptance tests (written before the code)

**C5, asking and reading**
1. Given a customer on their own order page, When they ask "Can we get the food at 11:30?", Then the question is
   stored with the time and shown on the page as waiting for an answer.
2. Given the question form, When the question is empty or longer than 1000 characters, Then nothing is stored, a
   message explains why, and the form keeps what was typed.
3. Given an order, When another customer posts a question to it, Then they get 404 and nothing is stored; a visitor
   is asked to log in; the admin is refused (P5-4).
4. Given a question that staff have answered, When the customer opens the order page, Then the answer is shown with
   its time and "Ekte Mat" as the one who answered; My orders shows "1 answered" for that order (US-21, criterion 2).
5. Given a question containing `<script>alert(1)</script>`, When it is shown to the customer and to staff, Then it is
   shown as text and never runs.

**A4, reading and answering**
6. Given waiting questions asked at different times, and an answered one, When the admin opens Questions, Then only
   the waiting ones are shown, the oldest first, each with order number, customer and asked time; `show=answered`
   and `show=all` show the others; an unknown `show` answers 404 (P5-7).
7. Given an order with questions, When the admin opens the staff order page, Then every question is shown, with an
   answer form for each unanswered one (US-21, criterion 1).
8. Given a waiting question, When the admin answers it, Then the answer, the time and the staff member are stored;
   an empty or too long answer is refused and nothing changes.
9. Given a question that was answered in another tab, When the admin answers it again from the old page, Then the
   first answer is kept and the page says it was already answered (P5-5).
10. Given a customer or a visitor, When they open or post to any `/admin/questions` page, Then they get 403 or are
    sent to log in, and nothing changes (the every-admin-route test, now with question ids).
11. Given waiting questions, When the admin opens the dashboard, Then it shows how many wait, with a link to them.
12. Given the question or answer form sent without a valid CSRF token, When it arrives, Then it is refused (400).

**Model, repository and seed**
13. Given question and answer texts, Then the length rules hold, spaces at the ends are removed, and answering an
    answered question raises an error (model test).
14. Given two staff saving an answer to the same question, Then the repository saves only the first (P5-5).
15. Given `python seed.py`, Then there are answered and waiting sample questions, all on orders of the right customer.

## 6. Out of scope (later plans or not in Oblig 4)

- The e-mail to the customer when an answer is saved (US-21 criterion 2): the answer on the order page and the count
  in My orders replace it for now (as for status changes, plan 4).
- Marking answers as read or highlighting new answers; editing or deleting questions and answers.
- Questions that are not about an order (a general contact form), and questions that arrive by phone or e-mail.
- Attachments.
- Measuring how fast questions are answered (NFR-19 covers booking requests only).

## 7. Risks and open points

- **Questions can contain health data.** A customer may write "my daughter has a nut allergy" in a question. The
  hint asks for no names (P5-3); the same open point as in plan 3, section 9.
- **A double click can store the same question twice.** Each click is a real POST; the second copy is visible and
  harmless, and staff can answer both. ASSUMPTION: not worth a submission key here (unlike orders, P3-7).
- **Plan 6 (Neo4j)** must implement the `QuestionRepository` too; its graph model already has a `Question` node.

## 8. Done when

- [x] Acceptance tests 1-15 pass, plus all earlier tests (305 tests).
- [x] Every rule test has been seen to fail when its rule is broken on purpose (as in plans 1-4).
- [x] Works from a fresh clone with the README commands.
- [x] Works on User1's Windows PC: 305 passed (2026-10-24).
- [x] Checked in a browser at 1200 px and 390 px (page width measured on every page); screenshots of the questions
      on the customer's order page, the admin questions list and the staff order page saved in `docs/screenshots/`.
- [x] `docs/report-notes.md` updated, and this plan gets a "What changed compared with the plan" section (below).
- [x] After merging: the tag `Obligatorisk-4` on `main`, created by User1 as the GitHub release "Obligatorisk 4 -
      Ekte Mat" on 2026-10-24, on the merge of pull request #19 (commit `14caa3a`).

## 9. What changed compared with the plan (pull request #18)

- **Built as planned:** P5-1 to P5-10, with no database change, and acceptance tests 1-15: `test_p5_at01` to
  `test_p5_at13` in `test_questions.py`; 10 is `test_at10` in `test_admin_items.py` (it now fills in question ids);
  14 in `test_repositories.py`, 15 in `test_shop_and_seed.py`.
- **Small additions found while building:**
  - **The dashboard no longer repeats each number** ("2" above "2 waiting for a reply"). The label carried the number
    since plan 4 so that a test could find it; the browser check made it visible. The tests now read the number next
    to the label, and plan 4's dashboard screenshot was taken again.
  - **"Less than a minute"** instead of "0 minutes" for a question asked just now.
  - **An answer that breaks the rules is shown again with the text kept**, on the staff order page, not only as a
    message: a 2001-character answer would otherwise be lost (the customer's question form works the same way).
  - Line breaks in questions and answers are kept with CSS (`white-space: pre-line`), never by writing HTML, so the
    text stays text (acceptance test 5).
- **Errors caught before merging:** both in my tests, not the code. The every-admin-route test first compared an order
  with itself, which is always true; it now checks the status fields. Test 5 first used two fixtures that share one
  browser session, so the "customer" would really have posted as the admin.
- **Verification:** 305 tests, also from a fresh clone with only the README commands. 15 rules were broken on purpose,
  one at a time, and each was caught; "answering is open to everyone" was caught only by the every-admin-route test,
  because it fills in question ids. Browser check at 1200 px and 390 px for customer and staff: an empty question, a
  2001-character answer (refused, text kept), an answer from an old tab (refused, first answer kept), and the
  customer reading the answer. No page wider than the screen, no server errors.
- **Windows:** User1 ran the tests on Windows on 2026-10-24: 305 passed.
- **Final check before the tag (2026-10-24):** a fresh clone of `main` after pull request #18 installs, seeds and
  passes all 305 tests; every page answers for a visitor, a customer and the admin, with no server errors; a
  customer gets 404 for another customer's order; no secrets, stray files or names in the repository.
