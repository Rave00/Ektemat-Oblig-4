# Ekte Mat Online

Ordering website for Ekte Mat AS, a fictional catering company in Bergen (INFO212, Oblig 4).
Customers browse the menu by event, fill a cart and submit orders; staff manage food items, images, orders
and questions in an admin panel. Synthetic data only.

## Layout (MVC)

- `app/models/`: domain classes and rules (`domain.py`), pictures (`images.py`), and all data access in `repositories/`.
  `repositories/base.py` is the interface; `repositories/sqlite/` is the **only** code that touches SQLite.
- `app/controllers/`: Flask blueprints `shop` (menu, cart), `account` (log in, orders, questions),
  `admin` (staff panel); `security.py` has log in, access rules and CSRF.
- `app/views/`: Jinja2 templates and static files.
- `app/__init__.py`: `create_app()`, the one place that chooses the storage (SQLite now, Neo4j in Oblig 5).

## Commands

```
pip install -r requirements.txt
python seed.py                    # resets the database with sample data
flask --app app run --debug       # http://127.0.0.1:5000
python -m pytest                  # all tests
```

## Team rules

- Plan first: every larger feature starts as `docs/plans/N - Name-With-Dashes.md`; code only after Rave approves it.
- Work on a branch `feature/N-name`; Rave reviews and merges on GitHub.
- All tests pass before every push. New behaviour gets a test.
- Never import `sqlite3` or the SQLite repositories outside `app/models/repositories/sqlite/`
  (enforced by `tests/test_architecture.py`).
- Business rules belong in `app/models/`, not in routes. Controllers stay thin.
- Every POST form includes `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`.
- Never commit `.env`, API keys, `instance/` or real personal data.
- Requirements: user stories and design come from the lab (`docs/requirements/`, `docs/design/`);
  use the `ektemat-requirements` skill when writing or changing stories.
- British English in the UI and docs; dates as YYYY-MM-DD; money in NOK.
