"""Repository interfaces: the only data operations controllers and scripts may use.

A storage technology (SQLite now, Neo4j in Oblig 5) implements these classes. Nothing outside the
implementation knows how or where the data is stored.
"""
from abc import ABC, abstractmethod

from ..domain import FoodItem, User


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> User:
        """Store a new user and return it with its id. The e-mail address must be unused."""

    @abstractmethod
    def get(self, user_id: int) -> User | None:
        """The user with this id, or None."""

    @abstractmethod
    def get_by_email(self, email: str) -> User | None:
        """The user with this e-mail address (case-insensitive), or None."""


class FoodItemRepository(ABC):
    @abstractmethod
    def list(self, published_only: bool = False) -> list[FoodItem]:
        """All food items ordered by name; only published ones if asked."""

    @abstractmethod
    def get(self, item_id: int) -> FoodItem | None:
        """The food item with this id, or None."""

    @abstractmethod
    def add(self, item: FoodItem) -> FoodItem:
        """Store a new food item and return it with its id."""

    @abstractmethod
    def update(self, item: FoodItem) -> None:
        """Save changes to an existing food item."""

    @abstractmethod
    def delete(self, item_id: int) -> None:
        """Remove a food item. Callers check is_ordered() first."""

    @abstractmethod
    def is_ordered(self, item_id: int) -> bool:
        """True if the item is part of any order (then it must not be deleted, only unpublished)."""


class Repositories(ABC):
    """All repositories of one storage technology, created once per application."""

    users: UserRepository
    food_items: FoodItemRepository

    @abstractmethod
    def initialise(self) -> None:
        """Prepare the storage (create what is missing). Never deletes data."""

    @abstractmethod
    def reset(self) -> None:
        """Delete all data and start empty. Used by the seed script and the tests."""
