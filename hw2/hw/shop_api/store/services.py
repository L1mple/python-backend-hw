"""
Service layer implementations for the shop API.

Services contain business logic and validation, while delegating
data access operations to repositories.
"""

from typing import Optional
from .interface import (
    ItemServiceInterface,
    CartServiceInterface,
    ItemRepositoryInterface,
    CartRepositoryInterface,
)
from .models import ItemEntity, ItemInfo, CartEntity, CartInfo, CartItemEntity


class ItemService(ItemServiceInterface):
    """Service for item business logic"""

    def __init__(self, item_repo: ItemRepositoryInterface):
        """
        Initialize service with an item repository.

        Args:
            item_repo: Repository for item data access
        """
        self.item_repo = item_repo

    def create_item(self, name: str, price: float) -> ItemEntity:
        """
        Create a new item with validation.

        Args:
            name: Item name
            price: Item price

        Returns:
            Created ItemEntity

        Raises:
            ValueError: If validation fails
        """
        # Validation
        if not name or not name.strip():
            raise ValueError("Item name cannot be empty")

        if price < 0:
            raise ValueError("Item price cannot be negative")

        # Create item
        info = ItemInfo(name=name.strip(), price=price, deleted=False)
        return self.item_repo.create(info)

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
        item = self.item_repo.find_by_id(item_id)
        if item is None:
            raise ValueError(f"Item with id {item_id} not found")
        return item

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
        # Validation
        if not name or not name.strip():
            raise ValueError("Item name cannot be empty")

        if price < 0:
            raise ValueError("Item price cannot be negative")

        # Update item
        info = ItemInfo(name=name.strip(), price=price, deleted=False)
        updated_item = self.item_repo.update(item_id, info)

        if updated_item is None:
            raise ValueError(f"Item with id {item_id} not found")

        return updated_item


class CartService(CartServiceInterface):
    """Service for cart business logic"""

    def __init__(
        self,
        cart_repo: CartRepositoryInterface,
        item_repo: ItemRepositoryInterface,
    ):
        """
        Initialize service with cart and item repositories.

        Args:
            cart_repo: Repository for cart data access
            item_repo: Repository for item data access (to validate items)
        """
        self.cart_repo = cart_repo
        self.item_repo = item_repo

    def create_cart(self) -> CartEntity:
        """
        Create a new empty cart.

        Returns:
            Created CartEntity
        """
        empty_info = CartInfo(items=[])
        return self.cart_repo.create(empty_info)

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
        cart = self.cart_repo.find_by_id(cart_id)
        if cart is None:
            raise ValueError(f"Cart with id {cart_id} not found")
        return cart

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
        # Validate cart exists
        cart = self.cart_repo.find_by_id(cart_id)
        if cart is None:
            raise ValueError(f"Cart with id {cart_id} not found")

        # Validate item exists (we check even deleted items exist in DB)
        # The repository will handle availability status
        cart_item = self.cart_repo.add_item(cart_id, item_id)
        if cart_item is None:
            raise ValueError(f"Item with id {item_id} not found")

        # Get updated cart
        updated_cart = self.cart_repo.find_by_id(cart_id)
        return updated_cart, cart_item

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
        cart = self.get_cart(cart_id)  # This validates cart exists

        total = 0.0
        for cart_item in cart.info.items:
            # Get item to get its price
            item = self.item_repo.find_by_id(cart_item.item_id)
            if item is not None:
                total += item.info.price * cart_item.quantity

        return total


# ============================================================================
# Factory Functions for Easy Service Creation
# ============================================================================


def create_item_service(item_repo: ItemRepositoryInterface) -> ItemService:
    """
    Factory function to create an ItemService.

    Args:
        item_repo: Item repository implementation

    Returns:
        Configured ItemService
    """
    return ItemService(item_repo)


def create_cart_service(
    cart_repo: CartRepositoryInterface,
    item_repo: ItemRepositoryInterface,
) -> CartService:
    """
    Factory function to create a CartService.

    Args:
        cart_repo: Cart repository implementation
        item_repo: Item repository implementation

    Returns:
        Configured CartService
    """
    return CartService(cart_repo, item_repo)
