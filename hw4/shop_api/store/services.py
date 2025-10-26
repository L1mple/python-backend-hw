from contextlib import contextmanager
from fastapi import HTTPException
from typing import List, Optional, Dict, Any
from sqlalchemy import text
from sqlalchemy.orm import Session
from shop_api.db.database import ItemDB, CartDB, CartItemDB
from shop_api.store.models import ItemResponse, CartResponse, CartItemResponse, ItemCreate

class ItemService:
    def __init__(self, db: Session):
        self.db = db

    def create_item(self, item: ItemCreate) -> ItemResponse:
        new_item = ItemDB(name=item.name, price=item.price)
        self.db.add(new_item)
        self.db.commit()
        self.db.refresh(new_item)
        return ItemResponse(id=new_item.id, name=new_item.name, price=new_item.price, deleted=False)

    def get_item(self, item_id: int) -> ItemResponse:
        item = self.db.query(ItemDB).filter(ItemDB.id == item_id, ItemDB.deleted == False).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return ItemResponse(id=item.id, name=item.name, price=item.price, deleted=False)

    def get_items(self, offset=0, limit=10, min_price=None, max_price=None, show_deleted=False):
        query = self.db.query(ItemDB)
        if not show_deleted:
            query = query.filter(ItemDB.deleted == False)
        if min_price:
            query = query.filter(ItemDB.price >= min_price)
        if max_price:
            query = query.filter(ItemDB.price <= max_price)
        items = query.offset(offset).limit(limit).all()
        return [ItemResponse(id=i.id, name=i.name, price=i.price, deleted=i.deleted) for i in items]

    def replace_item(self, item_id: int, item: ItemCreate) -> ItemResponse:
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail="Item not found")
        db_item.name = item.name
        db_item.price = item.price
        self.db.commit()
        self.db.refresh(db_item)
        return ItemResponse(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def update_item(self, item_id: int, updates: Dict[str, Any]) -> ItemResponse:
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail="Item not found")
        if db_item.deleted:
            raise HTTPException(status_code=400, detail="Cannot update deleted item")
        for key, value in updates.items():
            if key in ['name', 'price']:
                setattr(db_item, key, value)
        self.db.commit()
        self.db.refresh(db_item)
        return ItemResponse(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def delete_item(self, item_id: int):
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if db_item:
            db_item.deleted = True
            self.db.commit()

class CartService:
    def __init__(self, db: Session):
        self.db = db

    def create_cart(self):
        cart = CartDB(price=0.0)
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return {"id": cart.id}

    def get_cart(self, cart_id: int) -> CartResponse:
        cart = self.db.query(CartDB).filter(CartDB.id == cart_id).first()
        if not cart:
            raise HTTPException(status_code=404, detail="Cart not found")

        cart_items = self.db.query(CartItemDB).filter(CartItemDB.cart_id == cart_id).all()
        items = []
        total_price = 0.0

        for ci in cart_items:
            item = self.db.query(ItemDB).filter(ItemDB.id == ci.item_id).first()
            if item and not item.deleted:
                items.append(CartItemResponse(
                    id=ci.id,
                    name=item.name,
                    quantity=ci.quantity,
                    available=True
                ))
                total_price += ci.quantity * item.price
            else:
                items.append(CartItemResponse(
                    id=ci.id,
                    name=item.name if item else "Unknown Item",
                    quantity=ci.quantity,
                    available=False
                ))

        if abs(cart.price - total_price) > 0.001:
            cart.price = total_price
            self.db.commit()

        return CartResponse(id=cart.id, items=items, price=total_price)

    def get_carts(self, offset=0, limit=10, min_price=None, max_price=None, min_quantity=None, max_quantity=None):
        carts = self.db.query(CartDB).offset(offset).limit(limit).all()
        result = []
        for cart in carts:
            cart_items = self.db.query(CartItemDB).filter(CartItemDB.cart_id == cart.id).all()
            total_qty = sum(ci.quantity for ci in cart_items)
            if (min_price is None or cart.price >= min_price) and \
                    (max_price is None or cart.price <= max_price) and \
                    (min_quantity is None or total_qty >= min_quantity) and \
                    (max_quantity is None or total_qty <= max_quantity):
                result.append(self.get_cart(cart.id))
        return result

    def add_item_to_cart(self, cart_id: int, item_id: int):
        cart = self.db.query(CartDB).filter(CartDB.id == cart_id).first()
        item = self.db.query(ItemDB).filter(ItemDB.id == item_id, ItemDB.deleted == False).first()
        if not cart or not item:
            raise HTTPException(status_code=404, detail="Cart or item not found")

        existing = self.db.query(CartItemDB).filter(CartItemDB.cart_id == cart_id,
                                                    CartItemDB.item_id == item_id).first()
        if existing:
            existing.quantity += 1
        else:
            cart_item = CartItemDB(cart_id=cart_id, item_id=item_id, quantity=1, available=True)
            self.db.add(cart_item)

        cart_items = self.db.query(CartItemDB).filter(CartItemDB.cart_id == cart_id).all()
        cart.price = sum(
            ci.quantity * self.db.query(ItemDB).filter(ItemDB.id == ci.item_id).first().price
            for ci in cart_items
            if (item := self.db.query(ItemDB).filter(ItemDB.id == ci.item_id).first()) and not item.deleted
        )
        self.db.commit()

    @contextmanager
    def isolation_read_uncommitted(self):
        self.db.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
        yield
        self.db.commit()

    @contextmanager
    def isolation_read_committed(self):
        self.db.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
        yield
        self.db.commit()

    @contextmanager
    def isolation_repeatable_read(self):
        self.db.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
        yield
        self.db.commit()

    @contextmanager
    def isolation_serializable(self):
        self.db.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
        yield
        self.db.commit()

    def demo_dirty_read(self, item_id: int):
        with self.isolation_read_uncommitted():
            item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
            return {"dirty_price": item.price if item else None}

    def demo_non_repeatable_read(self, item_id: int):
        prices = []
        with self.isolation_read_committed():
            item1 = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
            prices.append(item1.price if item1 else None)

            item2 = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
            prices.append(item2.price if item2 else None)

        return {"price1": prices[0], "price2": prices[1]}

    def demo_phantom_read(self, min_price: float):
        count1 = 0
        with self.isolation_repeatable_read():
            count1 = self.db.query(ItemDB).filter(ItemDB.price >= min_price).count()

            count2 = self.db.query(ItemDB).filter(ItemDB.price >= min_price).count()

        return {"count1": count1, "count2": count2}
