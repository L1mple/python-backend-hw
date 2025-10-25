"""
Repository interfaces for the shop API using the Data Mapper pattern.

These interfaces define abstract contracts for data access operations,
allowing for different implementations (SQLAlchemy, in-memory, etc.)
while keeping the business logic decoupled from persistence details.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Iterable
from .models import (
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
    CartEntity,
    CartInfo,
    CartItemEntity,
)


class ItemRepositoryInterface(ABC):
    """Abstract interface for item repository operations"""

    @abstractmethod
    def create(self, info: ItemInfo) -> ItemEntity:
        """
        Create a new item in the repository.

        Args:
            info: Item information (name, price, deleted flag)

        Returns:
            ItemEntity with assigned ID
        """
        pass

    @abstractmethod
    def find_by_id(self, item_id: int) -> Optional[ItemEntity]:
        """
        Find an item by its ID.

        Args:
            item_id: The ID of the item to find

        Returns:
            ItemEntity if found and not deleted, None otherwise
        """
        pass

    @abstractmethod
    def find_many(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False,
    ) -> List[ItemEntity]:
        """
        Find multiple items with filtering and pagination.

        Args:
            offset: Number of items to skip
            limit: Maximum number of items to return
            min_price: Minimum price filter (inclusive)
            max_price: Maximum price filter (inclusive)
            show_deleted: Whether to include deleted items

        Returns:
            List of ItemEntity objects matching the criteria
        """
        pass

    @abstractmethod
    def update(self, item_id: int, info: ItemInfo) -> Optional[ItemEntity]:
        """
        Replace an item's information completely.

        Args:
            item_id: The ID of the item to update
            info: New item information

        Returns:
            Updated ItemEntity if found, None otherwise
        """
        pass

    @abstractmethod
    def patch(self, item_id: int, patch_info: PatchItemInfo) -> Optional[ItemEntity]:
        """
        Partially update an item's information.

        Args:
            item_id: The ID of the item to patch
            patch_info: Partial update information (only non-None fields are updated)

        Returns:
            Updated ItemEntity if found and not deleted, None otherwise
        """
        pass

    @abstractmethod
    def delete(self, item_id: int) -> Optional[ItemEntity]:
        """
        Mark an item as deleted (soft delete).

        Args:
            item_id: The ID of the item to delete

        Returns:
            Deleted ItemEntity if found, None otherwise
        """
        pass


class CartRepositoryInterface(ABC):
    """Abstract interface for cart repository operations"""

    @abstractmethod
    def create(self, info: CartInfo) -> CartEntity:
        """
        Create a new cart in the repository.

        Args:
            info: Cart information (list of cart items)

        Returns:
            CartEntity with assigned ID
        """
        pass

    @abstractmethod
    def find_by_id(self, cart_id: int) -> Optional[CartEntity]:
        """
        Find a cart by its ID.

        Args:
            cart_id: The ID of the cart to find

        Returns:
            CartEntity if found, None otherwise
        """
        pass

    @abstractmethod
    def find_many(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
    ) -> List[CartEntity]:
        """
        Find multiple carts with filtering and pagination.

        Args:
            offset: Number of carts to skip
            limit: Maximum number of carts to return
            min_price: Minimum total price filter (inclusive)
            max_price: Maximum total price filter (inclusive)
            min_quantity: Minimum number of items filter (inclusive)
            max_quantity: Maximum number of items filter (inclusive)

        Returns:
            List of CartEntity objects matching the criteria
        """
        pass

    @abstractmethod
    def add_item(self, cart_id: int, item_id: int) -> Optional[CartItemEntity]:
        """
        Add an item to a cart (or increment quantity if already present).

        Args:
            cart_id: The ID of the cart
            item_id: The ID of the item to add

        Returns:
            CartItemEntity (new or updated) if successful, None if cart or item not found
        """
        pass


class ItemServiceInterface(ABC):
    """Abstract interface for item business logic service"""

    @abstractmethod
    def create_item(self, name: str, price: float) -> ItemEntity:
        """
        Create a new item with validation.

        Args:
            name: Item name
            price: Item price

        Returns:
            Created ItemEntity

        Raises:
            ValueError: If validation fails (e.g., negative price, empty name)
        """
        pass

    @abstractmethod
    def get_item(self, item_id: int) -> ItemEntity:
        """
        Get an item by ID with existence validation.

        Args:
            item_id: The ID of the item

        Returns:
            ItemEntity if found

        Raises:
            ValueError: If item not found
        """
        pass

    @abstractmethod
    def update_item(self, item_id: int, name: str, price: float) -> ItemEntity:
        """
        Update an item with validation.

        Args:
            item_id: The ID of the item to update
            name: New item name
            price: New item price

        Returns:
            Updated ItemEntity

        Raises:
            ValueError: If validation fails or item not found
        """
        pass


class CartServiceInterface(ABC):
    """Abstract interface for cart business logic service"""

    @abstractmethod
    def create_cart(self) -> CartEntity:
        """
        Create a new empty cart.

        Returns:
            Created CartEntity
        """
        pass

    @abstractmethod
    def get_cart(self, cart_id: int) -> CartEntity:
        """
        Get a cart by ID with existence validation.

        Args:
            cart_id: The ID of the cart

        Returns:
            CartEntity if found

        Raises:
            ValueError: If cart not found
        """
        pass

    @abstractmethod
    def add_item_to_cart(
        self, cart_id: int, item_id: int
    ) -> tuple[CartEntity, CartItemEntity]:
        """
        Add an item to a cart with validation.

        Args:
            cart_id: The ID of the cart
            item_id: The ID of the item to add

        Returns:
            Tuple of (updated CartEntity, added/updated CartItemEntity)

        Raises:
            ValueError: If cart or item not found
        """
        pass

    @abstractmethod
    def calculate_cart_total(self, cart_id: int) -> float:
        """
        Calculate the total price of a cart.

        Args:
            cart_id: The ID of the cart

        Returns:
            Total price of all items in the cart

        Raises:
            ValueError: If cart not found
        """
        pass
