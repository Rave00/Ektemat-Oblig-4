"""Ekte Mat Online: application factory.

This is the composition root: the only place that decides which storage the repositories use.
Swapping SQLite for Neo4j (Oblig 5) means changing the repository class created below.
"""
import os
import secrets
from pathlib import Path

from flask import Flask, render_template

from .controllers import account, admin, security, shop
from .models.images import ImageStore
from .models.repositories.sqlite import SqliteRepositories


def create_app(test_config=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        template_folder="views/templates",   # VIEW layer (plan 0, decision D1)
        static_folder="views/static",
    )
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config.update(
        DATABASE=os.environ.get("DATABASE") or str(Path(app.instance_path) / "ektemat.db"),
        UPLOAD_FOLDER=str(Path(app.static_folder) / "uploads"),
        MAX_CONTENT_LENGTH=2 * 1024 * 1024 + 64 * 1024,   # a 2 MB picture plus the rest of the form (plan 1)
        CSRF_ENABLED=True,
    )
    if test_config:
        app.config.update(test_config)
    if not app.config.get("SECRET_KEY"):
        app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or _local_secret_key(app.instance_path)

    repositories = SqliteRepositories(app.config["DATABASE"])
    repositories.initialise()                 # creates missing tables; never deletes data
    app.extensions["repositories"] = repositories
    app.extensions["images"] = ImageStore(app.config["UPLOAD_FOLDER"])

    security.init_app(app)
    app.register_blueprint(shop.bp)
    app.register_blueprint(account.bp)
    app.register_blueprint(admin.bp)

    for code in (400, 403, 404, 413):
        app.register_error_handler(code, _error_page)
    return app


def _local_secret_key(instance_path):
    """A random key kept in instance/secret_key, so no secret is ever written in the code or in Git."""
    key_file = Path(instance_path) / "secret_key"
    if not key_file.exists():
        key_file.write_text(secrets.token_hex(32), encoding="utf-8")
    return key_file.read_text(encoding="utf-8").strip()


MESSAGES = {413: "The file is too large: pictures can be at most 2 MB."}


def _error_page(error):
    description = MESSAGES.get(error.code, error.description)
    return render_template("errors/error.html", error=error, description=description), error.code
