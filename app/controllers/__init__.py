"""CONTROLLER layer: Flask routes grouped in blueprints (shop, account, admin).

Controllers read the request, call the model (domain rules and repositories) and choose a view.
They never touch storage directly: `repos()` gives them the repository interfaces.
"""
from flask import current_app

from ..models.repositories.base import Repositories


def repos() -> Repositories:
    return current_app.extensions["repositories"]
