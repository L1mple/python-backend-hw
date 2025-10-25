"""
Concrete repository implementations for the shop API.

This module provides:
1. SQLAlchemy-based repositories for production use
2. In-memory repositories for testing
"""

from typing import List, Optional
from decimal import Decimal
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from .interface import ItemRepositoryInterface, CartRepositoryInterface
from .models import (
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
    CartEntity,
    CartInfo,
    CartItemEntity,
)
from .database import ItemOrm, CartOrm, CartItemOrm
from .mappers import ItemMapper, CartMapper


# ============================================================================
# SQLAlchemy Implementations
# ============================================================================


class SqlAlchemyItemRepository(ItemRepositoryInterface):
    """SQLAlchemy implementation of ItemRepositoryInterface"""

    def __init__(self, session: Session):
        """
        Initialize repository with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def create(self, info: ItemInfo) -> ItemEntity:
        """Create a new item in the database"""
        orm_item = ItemMapper.to_orm(info)
        self.session.add(orm_item)
        self.session.flush()  # Get ID without committing transaction
        return ItemMapper.to_domain(orm_item)

    def find_by_id(self, item_id: int) -> Optional[ItemEntity]:
        """Find an item by ID (returns None if deleted)"""
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()

        if orm_item is None or orm_item.deleted:
            return None

        return ItemMapper.to_domain(orm_item)

    def find_many(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False,
    ) -> List[ItemEntity]:
        """Find multiple items with filtering and pagination"""
        query = self.session.query(ItemOrm)

        # Apply filters
        if not show_deleted:
            query = query.filter(ItemOrm.deleted == False)

        if min_price is not None:
            query = query.filter(ItemOrm.price >= Decimal(str(min_price)))

        if max_price is not None:
            query = query.filter(ItemOrm.price <= Decimal(str(max_price)))

        # Apply pagination
        query = query.offset(offset).limit(limit)

        # Execute and map to domain models
        orm_items = query.all()
        return [ItemMapper.to_domain(orm_item) for orm_item in orm_items]

    def update(self, item_id: int, info: ItemInfo) -> Optional[ItemEntity]:
        """Replace an item's information completely"""
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()

        if orm_item is None:
            return None

        # Update all fields
        ItemMapper.to_orm(info, orm_item)
        self.session.flush()
        return ItemMapper.to_domain(orm_item)

    def patch(self, item_id: int, patch_info: PatchItemInfo) -> Optional[ItemEntity]:
        """Partially update an item's information"""
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()

        if orm_item is None or orm_item.deleted:
            return None

        # Update only provided fields
        if patch_info.name is not None:
            orm_item.name = patch_info.name

        if patch_info.price is not None:
            orm_item.price = Decimal(str(patch_info.price))

        self.session.flush()
        return ItemMapper.to_domain(orm_item)

    def delete(self, item_id: int) -> Optional[ItemEntity]:
        """Mark an item as deleted (soft delete)"""
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()

        if orm_item is None:
            return None

        orm_item.deleted = True
        self.session.flush()
        return ItemMapper.to_domain(orm_item)


class SqlAlchemyCartRepository(CartRepositoryInterface):
    """SQLAlchemy implementation of CartRepositoryInterface"""

    def __init__(self, session: Session):
        """
        Initialize repository with a database session.

        Args:
            session: SQLAlchemy session for database operations
        """
        self.session = session

    def create(self, info: CartInfo) -> CartEntity:
        """Create a new cart in the database"""
        orm_cart = CartOrm()
        self.session.add(orm_cart)
        self.session.flush()  # Get ID

        # Add cart items if provided
        for cart_item in info.items:
            orm_cart_item = CartItemOrm(
                cart_id=orm_cart.id,
                item_id=cart_item.item_id,
                item_name=cart_item.item_name,
                quantity=cart_item.quantity,
                available=cart_item.available,
            )
            self.session.add(orm_cart_item)

        self.session.flush()
        # Refresh to load relationships
        self.session.refresh(orm_cart)
        return CartMapper.to_domain(orm_cart)

    def find_by_id(self, cart_id: int) -> Optional[CartEntity]:
        """Find a cart by ID"""
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()

        if orm_cart is None:
            return None

        return CartMapper.to_domain(orm_cart)

    def find_many(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
    ) -> List[CartEntity]:
        """Find multiple carts with filtering and pagination"""
        query = self.session.query(CartOrm)

        # For price and quantity filters, we need to apply them in Python
        # since they involve calculations across related tables
        all_carts = (
            query.offset(offset).limit(limit * 10).all()
        )  # Get more for filtering

        filtered_carts = []
        for orm_cart in all_carts:
            # Calculate cart metrics
            total_price = sum(
                float(item.item.price) * item.quantity
                for item in orm_cart.items
                if item.item is not None
            )
            item_count = len(orm_cart.items)

            # Apply filters
            if min_price is not None and total_price < min_price:
                continue
            if max_price is not None and total_price > max_price:
                continue
            if min_quantity is not None and item_count < min_quantity:
                continue
            if max_quantity is not None and item_count > max_quantity:
                continue

            filtered_carts.append(orm_cart)

            # Stop if we have enough results
            if len(filtered_carts) >= limit:
                break

        return [CartMapper.to_domain(orm_cart) for orm_cart in filtered_carts]

    def add_item(self, cart_id: int, item_id: int) -> Optional[CartItemEntity]:
        """Add an item to a cart or increment quantity if already present"""
        # Check if cart exists
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        if orm_cart is None:
            return None

        # Check if item exists
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        if orm_item is None:
            return None

        # Check if item already in cart
        existing_cart_item = (
            self.session.query(CartItemOrm)
            .filter_by(cart_id=cart_id, item_id=item_id)
            .first()
        )

        if existing_cart_item:
            # Increment quantity
            existing_cart_item.quantity += 1
            self.session.flush()
            return CartItemEntity(
                item_id=existing_cart_item.item_id,
                item_name=existing_cart_item.item_name,
                quantity=existing_cart_item.quantity,
                available=existing_cart_item.available,
            )
        else:
            # Create new cart item
            new_cart_item = CartItemOrm(
                cart_id=cart_id,
                item_id=item_id,
                item_name=orm_item.name,
                quantity=1,
                available=not orm_item.deleted,
            )
            self.session.add(new_cart_item)
            self.session.flush()
            return CartItemEntity(
                item_id=new_cart_item.item_id,
                item_name=new_cart_item.item_name,
                quantity=new_cart_item.quantity,
                available=new_cart_item.available,
            )


# ============================================================================
# In-Memory Implementations (for testing)
# ============================================================================


class InMemoryItemRepository(ItemRepositoryInterface):
    """In-memory implementation of ItemRepositoryInterface for testing"""

    def __init__(self):
        """Initialize with empty storage"""
        self._storage: dict[int, ItemInfo] = {}
        self._next_id = 0

    def create(self, info: ItemInfo) -> ItemEntity:
        """Create a new item in memory"""
        item_id = self._next_id
        self._next_id += 1
        self._storage[item_id] = ItemInfo(
            name=info.name,
            price=info.price,
            deleted=info.deleted,
        )
        return ItemEntity(id=item_id, info=self._storage[item_id])

    def find_by_id(self, item_id: int) -> Optional[ItemEntity]:
        """Find an item by ID"""
        if item_id not in self._storage or self._storage[item_id].deleted:
            return None
        return ItemEntity(id=item_id, info=self._storage[item_id])

    def find_many(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False,
    ) -> List[ItemEntity]:
        """Find multiple items with filtering"""
        results = []
        count = 0

        for item_id, info in self._storage.items():
            # Apply filters
            if not show_deleted and info.deleted:
                continue
            if min_price is not None and info.price < min_price:
                continue
            if max_price is not None and info.price > max_price:
                continue

            # Apply pagination
            if count >= offset:
                results.append(ItemEntity(id=item_id, info=info))
                if len(results) >= limit:
                    break
            count += 1

        return results

    def update(self, item_id: int, info: ItemInfo) -> Optional[ItemEntity]:
        """Replace an item's information"""
        if item_id not in self._storage:
            return None

        self._storage[item_id] = ItemInfo(
            name=info.name,
            price=info.price,
            deleted=info.deleted,
        )
        return ItemEntity(id=item_id, info=self._storage[item_id])

    def patch(self, item_id: int, patch_info: PatchItemInfo) -> Optional[ItemEntity]:
        """Partially update an item"""
        if item_id not in self._storage or self._storage[item_id].deleted:
            return None

        curr_info = self._storage[item_id]

        if patch_info.name is not None:
            curr_info.name = patch_info.name
        if patch_info.price is not None:
            curr_info.price = patch_info.price

        return ItemEntity(id=item_id, info=curr_info)

    def delete(self, item_id: int) -> Optional[ItemEntity]:
        """Mark an item as deleted"""
        if item_id not in self._storage:
            return None

        self._storage[item_id].deleted = True
        return ItemEntity(id=item_id, info=self._storage[item_id])


class InMemoryCartRepository(CartRepositoryInterface):
    """In-memory implementation of CartRepositoryInterface for testing"""

    def __init__(self, item_repo: InMemoryItemRepository):
        """
        Initialize with empty storage.

        Args:
            item_repo: Item repository for looking up item information
        """
        self._storage: dict[int, CartInfo] = {}
        self._next_id = 0
        self._item_repo = item_repo

    def create(self, info: CartInfo) -> CartEntity:
        """Create a new cart in memory"""
        cart_id = self._next_id
        self._next_id += 1
        self._storage[cart_id] = CartInfo(items=list(info.items))
        return CartEntity(id=cart_id, info=self._storage[cart_id])

    def find_by_id(self, cart_id: int) -> Optional[CartEntity]:
        """Find a cart by ID"""
        if cart_id not in self._storage:
            return None
        return CartEntity(id=cart_id, info=self._storage[cart_id])

    def find_many(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
    ) -> List[CartEntity]:
        """Find multiple carts with filtering"""
        results = []
        count = 0

        for cart_id, info in self._storage.items():
            # Calculate cart metrics
            total_price = 0.0
            for cart_item in info.items:
                item = self._item_repo.find_by_id(cart_item.item_id)
                if item:
                    total_price += item.info.price * cart_item.quantity

            item_count = len(info.items)

            # Apply filters
            if min_price is not None and total_price < min_price:
                continue
            if max_price is not None and total_price > max_price:
                continue
            if min_quantity is not None and item_count < min_quantity:
                continue
            if max_quantity is not None and item_count > max_quantity:
                continue

            # Apply pagination
            if count >= offset:
                results.append(CartEntity(id=cart_id, info=info))
                if len(results) >= limit:
                    break
            count += 1

        return results

    def add_item(self, cart_id: int, item_id: int) -> Optional[CartItemEntity]:
        """Add an item to a cart or increment quantity"""
        if cart_id not in self._storage:
            return None

        # Check if item exists
        item = self._item_repo.find_by_id(item_id)
        if item is None:
            # Try to get even deleted items
            if item_id not in self._item_repo._storage:
                return None
            item_info = self._item_repo._storage[item_id]
            item_name = item_info.name
            available = not item_info.deleted
        else:
            item_name = item.info.name
            available = not item.info.deleted

        cart_info = self._storage[cart_id]

        # Check if item already in cart
        for cart_item in cart_info.items:
            if cart_item.item_id == item_id:
                cart_item.quantity += 1
                return cart_item

        # Add new item to cart
        new_cart_item = CartItemEntity(
            item_id=item_id,
            item_name=item_name,
            quantity=1,
            available=available,
        )
        cart_info.items.append(new_cart_item)
        return new_cart_item
