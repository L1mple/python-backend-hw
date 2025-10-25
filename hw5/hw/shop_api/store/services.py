from contextlib import contextmanager

from fastapi import HTTPException
from typing import List, Optional, Dict, Any

from sqlalchemy import text
from sqlalchemy.orm import Session
from hw4.hw.shop_api.db.database import ItemDB, CartDB, CartItemDB
from hw4.hw.shop_api.store.models import ItemResponse, CartResponse, CartItemResponse, ItemCreate


class ItemService:
    def __init__(self, db: Session):
        self.db = db

    def create_item(self, item: ItemCreate) -> ItemResponse:
        new_item = ItemDB(name=item.name, price=item.price)
        self.db.add(new_item)
        self.db.flush()
        self.db.commit()
        return ItemResponse(id=new_item.id, name=new_item.name, price=new_item.price, deleted=False)

    def get_item(self, item_id: int) -> ItemResponse:
        item = self.db.query(ItemDB).filter(ItemDB.id == item_id, ItemDB.deleted == False).first()
        if not item:
            raise HTTPException(404, "Item not found")
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
            raise HTTPException(404, "Item not found")
        db_item.name = item.name
        db_item.price = item.price
        self.db.flush()
        self.db.commit()
        return ItemResponse(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def update_item(self, item_id: int, updates: Dict[str, Any]) -> ItemResponse:
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if not db_item:
            return None  # Вместо raise HTTPException(404, "Item not found")
        if db_item.deleted:
            raise HTTPException(304)
        for key, value in updates.items():
            if key in ['name', 'price']:
                setattr(db_item, key, value)
        self.db.flush()
        self.db.commit()
        return ItemResponse(id=db_item.id, name=db_item.name, price=db_item.price, deleted=db_item.deleted)

    def delete_item(self, item_id: int):
        db_item = self.db.query(ItemDB).filter(ItemDB.id == item_id).first()
        if db_item:
            db_item.deleted = True
            self.db.flush()
            self.db.commit()


class CartService:
    def __init__(self, db: Session):
        self.db = db

    def create_cart(self):
        cart = CartDB(price=0.0)
        self.db.add(cart)
        self.db.flush()
        self.db.commit()
        return {"id": cart.id}

    def get_cart(self, cart_id: int) -> CartResponse:
        cart = self.db.query(CartDB).filter(CartDB.id == cart_id).first()
        if not cart:
            raise HTTPException(404, "Cart not found")

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
            raise HTTPException(404, "Cart or item not found")

        existing = self.db.query(CartItemDB).filter(CartItemDB.cart_id == cart_id,
                                                    CartItemDB.item_id == item_id).first()
        if existing:
            existing.quantity += 1
        else:
            cart_item = CartItemDB(cart_id=cart_id, item_id=item_id, quantity=1, available=True)
            self.db.add(cart_item)

        # Пересчитать цену
        cart_items = self.db.query(CartItemDB).filter(CartItemDB.cart_id == cart_id).all()
        cart.price = sum(
            ci.quantity * self.db.query(ItemDB).filter(ItemDB.id == ci.item_id).first().price
            for ci in cart_items
            if (item := self.db.query(ItemDB).filter(ItemDB.id == ci.item_id).first()) and not item.deleted
        )
        self.db.flush()
        self.db.commit()
