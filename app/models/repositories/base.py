"""Repository interfaces: the only data operations controllers and scripts may use.

A storage technology (SQLite now, Neo4j in Oblig 5) implements these classes. Nothing outside the
implementation knows how or where the data is stored.
"""
from __future__ import annotations      # type hints as text: the method `list` must not hide list[...]

from abc import ABC, abstractmethod
from datetime import date

from ..domain import FoodItem, Order, User


class EmailAlreadyUsed(Exception):
    """A user with this e-mail address (in any upper or lower case) already exists.

    Every storage raises this same error, so pages and tests never see a database's own error (plan 6, P6-7).
    """


class UserRepository(ABC):
    @abstractmethod
    def add(self, user: User) -> User:
        """Store a new user and return it with its id. Raises EmailAlreadyUsed if the address is taken."""

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


class OrderRepository(ABC):
    @abstractmethod
    def add(self, order: Order) -> Order:
        """Store an order with its lines and guest groups, all or nothing, and return it as stored.

        If an order with the same submission key already exists, nothing new is stored and that order is
        returned instead (one order per click, plan 3, P3-7).
        """

    @abstractmethod
    def get(self, order_id: int) -> Order | None:
        """The order with this id, with its lines (and the dishes' names) and guest groups, or None."""

    @abstractmethod
    def get_by_submission_key(self, key: str) -> Order | None:
        """The order that was stored from the form with this key, or None."""

    @abstractmethod
    def list(self, status: str | None = None, date_from: date | None = None,
             date_to: date | None = None) -> list[Order]:
        """All orders with their lines and the customer's name and e-mail, soonest event date first (plan 4, P4-6).

        Only one status if `status` is given; only event dates from `date_from` to `date_to`, both days included.
        """

    @abstractmethod
    def list_for_customer(self, customer_id: int) -> list[Order]:
        """One customer's orders with their lines, newest first (plan 4, P4-8)."""

    @abstractmethod
    def update_status(self, order: Order, expected_status: str) -> bool:
        """Save the order's status, status reason and first reply time, but only if the stored status is still
        `expected_status` (plan 4, P4-4). Returns False, and saves nothing, if someone changed it in the meantime."""

    @abstractmethod
    def update_payment_status(self, order_id: int, payment_status: str) -> None:
        """Save a new payment status (plan 4, P4-5)."""


class Repositories(ABC):
    """All repositories of one storage technology, created once per application."""

    users: UserRepository
    food_items: FoodItemRepository
    orders: OrderRepository

    @abstractmethod
    def initialise(self) -> None:
        """Prepare the storage (create what is missing). Never deletes data."""

    @abstractmethod
    def reset(self) -> None:
        """Delete all data and start empty. Used by the seed script and the tests."""
