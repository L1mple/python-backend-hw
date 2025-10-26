from dataclasses import dataclass, field
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
import uuid

from ..database import ItemDB, CartDB, CartItemDB
from .storage import ItemData, CartData, ItemnInCartData


@dataclass(slots=True)
class DBStorage:
    """Database-backed storage class for managing items and carts."""

    db: Session

    def add_item(self, name: str, price: float) -> ItemData:
        """Add a new item to database and return it."""
        # Generate ID from first 8 hex chars of uuid4 (32-bit)
        item_id = int(uuid.uuid4().hex[:8], 16)
        db_item = ItemDB(id=item_id, name=name, price=price, deleted=False)
        self.db.add(db_item)
        self.db.commit()
        self.db.refresh(db_item)
        return ItemData(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def create_cart(self) -> CartData:
        """Create a new empty cart and return it."""
        # Generate ID from first 8 hex chars of uuid4 (32-bit)
        cart_id = int(uuid.uuid4().hex[:8], 16)
        db_cart = CartDB(id=cart_id, price=0.0)
        self.db.add(db_cart)
        self.db.commit()
        self.db.refresh(db_cart)
        return CartData(id=db_cart.id, items=[], price=db_cart.price)

    def get_item(self, id: int) -> ItemData:
        """Get item by ID."""
        db_item = self.db.query(ItemDB).filter(ItemDB.id == id).first()
        if not db_item:
            raise KeyError(f"Item {id} not found")
        if db_item.deleted:
            raise KeyError(f"Item {id} not found")
        return ItemData(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def get_cart(self, id: int) -> CartData:
        """Get cart by ID."""
        db_cart = self.db.query(CartDB).filter(CartDB.id == id).first()
        if not db_cart:
            raise KeyError(f"Cart {id} not found")

        # Build cart items list
        cart_items = []
        for cart_item in db_cart.cart_items:
            item = cart_item.item
            cart_items.append(ItemnInCartData(
                id=item.id,
                name=item.name,
                quantity=cart_item.quantity,
                available=not item.deleted
            ))

        return CartData(id=db_cart.id, items=cart_items, price=db_cart.price)

    def get_items(self,
                offset: int = 0,
                limit: int = 10,
                min_price: Optional[float] = None,
                max_price: Optional[float] = None,
                show_deleted: bool = False) -> List[ItemData]:
        """Get all items with filters."""
        query = self.db.query(ItemDB)

        if not show_deleted:
            query = query.filter(ItemDB.deleted == False)
        if min_price is not None:
            query = query.filter(ItemDB.price >= min_price)
        if max_price is not None:
            query = query.filter(ItemDB.price <= max_price)

        db_items = query.offset(offset).limit(limit).all()
        return [ItemData(id=item.id, name=item.name, price=item.price, deleted=item.deleted)
                for item in db_items]

    def get_carts(self,
                offset: int = 0,
                limit: int = 10,
                min_price: Optional[float] = None,
                max_price: Optional[float] = None,
                min_quantity: Optional[int] = None,
                max_quantity: Optional[int] = None) -> List[CartData]:
        """Get all carts with filters."""
        query = self.db.query(CartDB)

        if min_price is not None:
            query = query.filter(CartDB.price >= min_price)
        if max_price is not None:
            query = query.filter(CartDB.price <= max_price)

        db_carts = query.offset(offset).limit(limit).all()

        # Convert to CartData and filter by quantity if needed
        carts = []
        for db_cart in db_carts:
            cart_items = []
            total_quantity = 0

            for cart_item in db_cart.cart_items:
                item = cart_item.item
                cart_items.append(ItemnInCartData(
                    id=item.id,
                    name=item.name,
                    quantity=cart_item.quantity,
                    available=not item.deleted
                ))
                total_quantity += cart_item.quantity

            # Apply quantity filters
            if min_quantity is not None and total_quantity < min_quantity:
                continue
            if max_quantity is not None and total_quantity > max_quantity:
                continue

            carts.append(CartData(id=db_cart.id, items=cart_items, price=db_cart.price))

        return carts

    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        """Add item to cart, updating quantity if item already exists. Returns True if successful."""
        db_cart = self.db.query(CartDB).filter(CartDB.id == cart_id).first()
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()

        if not db_cart or not db_item:
            return False

        # Check if item already in cart
        cart_item = self.db.query(CartItemDB).filter(
            and_(CartItemDB.cart_id == cart_id, CartItemDB.item_id == item_id)
        ).first()

        if cart_item:
            # Update quantity
            cart_item.quantity += 1
        else:
            # Add new item to cart
            cart_item = CartItemDB(cart_id=cart_id, item_id=item_id, quantity=1)
            self.db.add(cart_item)

        # Flush to make the new item visible to the relationship
        self.db.flush()

        # Recalculate cart price
        self._recalculate_cart_price(db_cart)

        self.db.commit()
        return True

    def put_item(self, item_id: int, name: str, price: float) -> ItemData:
        """Update item completely."""
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if not db_item:
            raise KeyError(f"Item {item_id} not found")

        db_item.name = name
        db_item.price = price

        # Update all carts containing this item
        self._update_affected_carts(item_id)

        self.db.commit()
        self.db.refresh(db_item)
        return ItemData(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def patch_item(self, item_id: int, name: Optional[str], price: Optional[float]) -> ItemData:
        """Partially update item."""
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if not db_item:
            raise KeyError(f"Item {item_id} not found")

        if name is not None:
            db_item.name = name
        if price is not None:
            db_item.price = price
            # Update all carts containing this item
            self._update_affected_carts(item_id)

        self.db.commit()
        self.db.refresh(db_item)
        return ItemData(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def soft_delete_item(self, item_id: int) -> ItemData:
        """Soft delete an item."""
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if not db_item:
            raise KeyError(f"Item {item_id} not found")

        db_item.deleted = True

        # Update all carts containing this item
        self._update_affected_carts(item_id)

        self.db.commit()
        self.db.refresh(db_item)
        return ItemData(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def _recalculate_cart_price(self, db_cart: CartDB):
        """Recalculate total price for a cart."""
        total_price = 0.0
        for cart_item in db_cart.cart_items:
            item = cart_item.item
            # Include all items in price calculation, matching original storage behavior
            total_price += item.price * cart_item.quantity
        db_cart.price = total_price

    def _update_affected_carts(self, item_id: int):
        """Update prices for all carts containing the specified item."""
        cart_items = self.db.query(CartItemDB).filter(CartItemDB.item_id == item_id).all()
        affected_cart_ids = {ci.cart_id for ci in cart_items}

        for cart_id in affected_cart_ids:
            db_cart = self.db.query(CartDB).filter(CartDB.id == cart_id).first()
            if db_cart:
                self._recalculate_cart_price(db_cart)
