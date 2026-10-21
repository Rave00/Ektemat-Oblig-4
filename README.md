# Ekte Mat Online

A first version of the ordering website for **Ekte Mat AS**, a fictional catering company in Bergen.
INFO212 Systemutvikling, autumn 2026, Obligatory assignment 4. Built with Flask (MVC) and Claude Code.
All data is synthetic.

## Requirements

Python 3.11 or newer.

## Install, seed, run and test

**Windows (PowerShell)**, from the repository folder:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python seed.py
flask --app app run --debug
```

**macOS / Linux:**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python seed.py
flask --app app run --debug
```

Open <http://127.0.0.1:5000>. Run the tests with:

```
python -m pytest
```

If PowerShell refuses to run `Activate.ps1`, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, or use `.venv\Scripts\activate.bat` in cmd.

## Test accounts (created by `python seed.py`, development only)

| Role | E-mail | Password |
|---|---|---|
| Admin | admin@ektemat.example | admin-dev-1 |
| Customer | kunde1@example.com | customer-dev-1 |
| Customer | kunde2@example.com | customer-dev-2 |

`python seed.py` deletes all existing data and starts again.

## Structure (Model-View-Controller)

```
app/
  models/          domain classes, rules and data access
    repositories/  base.py = interface, sqlite/ = the only code that touches the database
  controllers/     Flask blueprints: shop, account, admin (+ security helpers)
  views/           Jinja2 templates and static files
tests/             pytest, including architecture rules
docs/plans/        the agreed plan for every larger feature
docs/design/       diagrams from the analysis (lab exercise)
docs/requirements/ product backlog (user stories) from the lab exercise
seed.py            synthetic sample data
```

The database is SQLite for now (`instance/ektemat.db`, created automatically). Only the repository classes
use it, so Neo4j can replace it in Obligatory assignment 5 without changes to controllers or views.

## Configuration

Nothing is required. Optional environment variables: `SECRET_KEY` (otherwise a random key is created in
`instance/secret_key`) and `DATABASE` (path to the SQLite file). See `.env.example`.
No API keys are used or stored in this repository.
