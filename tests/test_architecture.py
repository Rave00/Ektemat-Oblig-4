"""Architecture rules from plan 0 (D1, D3, D4), checked on every test run.

The assignment: only repository classes in the model layer may touch the temporary store, so Neo4j can
replace it later without changes to controllers or views.
"""
import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[1] / "app"
SQLITE_PACKAGE = APP / "models" / "repositories" / "sqlite"
CONTROLLERS = APP / "controllers"


def imported_modules(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            yield "." * node.level + (node.module or "")


def python_files(folder):
    return sorted(folder.rglob("*.py"))


def test_the_three_mvc_layers_are_folders():
    for layer in ("models", "views", "controllers"):
        assert (APP / layer).is_dir(), f"missing layer folder app/{layer}"


def test_views_are_served_from_the_views_folder(app):
    assert Path(app.root_path, app.template_folder) == APP / "views" / "templates"
    assert Path(app.static_folder) == APP / "views" / "static"


def test_only_the_sqlite_repositories_import_sqlite3():
    users = [p for p in python_files(APP) if "sqlite3" in imported_modules(p)]
    assert users, "expected the SQLite repositories to import sqlite3"
    outside = [str(p.relative_to(APP)) for p in users if SQLITE_PACKAGE not in p.parents]
    assert outside == [], f"sqlite3 used outside the repositories: {outside}"


def test_controllers_do_not_use_the_storage_implementation():
    offenders = [f"{p.relative_to(APP)} imports {m}"
                 for p in python_files(CONTROLLERS) for m in imported_modules(p) if "sqlite" in m]
    assert offenders == [], offenders
