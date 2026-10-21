"""CONTROLLER layer: Flask routes grouped in blueprints (shop, account, admin).

Controllers read the request, call the model (domain rules and repositories) and choose a view.
They never touch storage directly: `repos()` gives them the repository interfaces and
`images()` the picture store.
"""
from flask import current_app

from ..models.images import ImageStore
from ..models.repositories.base import Repositories


def repos() -> Repositories:
    return current_app.extensions["repositories"]


def images() -> ImageStore:
    return current_app.extensions["images"]
