from typing import List, Optional
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from hw2.hw.shop_api.entities import Cart, Item, CartItem, Base
from hw2.hw.shop_api.patch_result import PatchResult

from hw2.hw.shop_api.contracts import PutItemRequest
from .models import (
    CartEntity,
    CartInfo,
    CartItemEntity,
    CartItemInfo,
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)

import os

class DatabaseStore:
    def __init__(self):
        database_url = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")
        
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        Base.metadata.create_all(bind=self.engine)
    
    @contextmanager 
    def get_session(self):
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def create_cart(self) -> int:
        with self.get_session() as session:
            cart_orm = Cart()
            session.add(cart_orm)
            session.flush()
            return cart_orm.id
    
    def add_item(self, info: ItemInfo) -> ItemEntity:
        with self.get_session() as session:
            item = Item(
                name=str(info.name),
                price=float(info.price),
                deleted=bool(info.deleted)
            )
            session.add(item)
            session.flush()
            
            return ItemEntity(
                id=item.id,
                info=ItemInfo(
                    name=str(item.name),
                    price=float(item.price),
                    deleted=bool(item.deleted)
                )
            )
    
    def get_cart(self, id: int) -> Optional[CartEntity]:
        with self.get_session() as session:
            cart_orm =session.query(Cart).filter(Cart.id == id).first()
            if not cart_orm:
                return None

            cart_items_orm = session.query(CartItem).filter(CartItem.cart_id == id).all()
            items: List[CartItem] = []
            total_price = 0.0

            for cart_item in cart_items_orm:
                item_orm = session.query(Item).filter(Item.id == cart_item.item_id).first()
                if item_orm:
                    items.append(
                        CartItemEntity(
                            id=item_orm.id,
                            info = CartItemInfo(
                                name=item_orm.name,
                                quantity=cart_item.quantity,
                                available=not item_orm.deleted
                            )
                        )
                    )
                    if not item_orm.deleted:
                        total_price += float(item_orm.price) * cart_item.quantity

            return CartEntity(
                id=id,
                info = CartInfo(
                    items=items,
                    price=total_price
                )
            )
    
    def get_all_carts(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        min_quantity: int | None = None,
        max_quantity: int | None = None,
    ) -> List[CartEntity]:
        with self.get_session() as session:
            cart_ids = session.query(Cart.id).offset(offset).limit(limit).all()
            carts: List[CartEntity] = []

            for (cart_id,) in cart_ids:
                cart: CartEntity | None = self.get_cart(cart_id)
                if cart:
                    if min_price is not None and cart.info.price < min_price:
                        continue
                    if max_price is not None and cart.info.price > max_price:
                        continue

                    total_quantity = sum(item.info.quantity for item in cart.info.items)
                    if min_quantity is not None and total_quantity < min_quantity:
                        continue
                    if max_quantity is not None and total_quantity > max_quantity:
                        continue

                    carts.append(cart)

            return carts
    
    def get_item(self, id: int) -> Optional[ItemEntity]:
        with self.get_session() as session:
            item = session.get(Item, id)
            if not item or item.deleted:
                return None
            
            return ItemEntity(
                id=int(item.id),
                info=ItemInfo(
                    name=str(item.name),
                    price=float(item.price),
                    deleted=bool(item.deleted)
                )
            )
    
    def get_all_items(self) -> List[ItemEntity]:
        with self.get_session() as session:
            items = session.execute(select(Item)).scalars().all()
            return [
                ItemEntity(
                    id=int(item.id),
                    info=ItemInfo(
                        name=str(item.name),
                        price=float(item.price),
                        deleted=bool(item.deleted)
                    )
                )
                for item in items
            ]
    
    def add_item_to_cart(self, cart_id: int, item: ItemEntity) -> bool:
        with self.get_session() as session:
            cart_orm = session.query(Cart).filter(Cart.id == cart_id).first()
            if not cart_orm:
                return False

            item_orm = session.query(Item).filter(Item.id == item.id).first()
            if not item_orm:
                return False

            cart_item = session.query(CartItem).filter(
                CartItem.cart_id == cart_id,
                CartItem.item_id == item.id
            ).first()

            if cart_item:
                cart_item.quantity += 1
            else:
                cart_item = CartItem(cart_id=cart_id, item_id=item.id, quantity=1)
                session.add(cart_item)

            return True
    
    def put_item(self, item_id: int, request: PutItemRequest) -> Optional[ItemEntity]:
        with self.get_session() as session:
            item_orm = session.query(Item).filter(Item.id == item_id).first()
            if not item_orm:
                return None
            item_orm.name = request.name
            item_orm.price = request.price
            session.commit()
            session.refresh(item_orm)
            return ItemEntity(
                id=item_orm.id,
                info = ItemInfo(
                    name=item_orm.name,
                    price=float(item_orm.price),
                    deleted=item_orm.deleted
                )
            )
    
    def patch_item(self, item_id: int, patch_info: PatchItemInfo) -> ItemEntity | PatchResult :
        with self.get_session() as session:
            item_orm = session.query(Item).filter(Item.id == item_id).first()
            if not item_orm:
                return PatchResult.NotModified

            if item_orm.deleted:
                 return PatchResult.NotModified

            if patch_info.name is not None:
                item_orm.name = patch_info.name
            if patch_info.price is not None:
                item_orm.price = patch_info.price

            session.commit()
            session.refresh(item_orm)
            return ItemEntity(
                id=item_orm.id,
                info = ItemInfo(
                    name=item_orm.name,
                    price=float(item_orm.price),
                    deleted=item_orm.deleted
                )
            )
    
    def delete_item(self, item_id: int) -> None:
        with self.get_session() as session:
            item_orm = session.query(Item).filter(Item.id == item_id).first()
            if item_orm:
                item_orm.deleted = True
                session.commit()
            
store = DatabaseStore()