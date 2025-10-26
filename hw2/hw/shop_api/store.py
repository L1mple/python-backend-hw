from typing import List

from enum import Enum
from sqlalchemy import create_engine, select, delete, and_
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager

from hw2.hw.shop_api.entities import Cart, Item, CartItemAssociation, base

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

def get_database_url():
    default_url = "postgresql://shop_user:shop_password@postgres:5432/shop_db"
    url = os.getenv('DATABASE_URL', default_url)
    
    return url

class DatabaseStore:
    
    def __init__(self, database_url: str = get_database_url()):
        self.engine = create_engine(database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        base.metadata.create_all(bind=self.engine)
        
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
            cart = Cart()
            session.add(cart)
            session.flush()
            cart_id = cart.id
            return cart_id

    def add_item(self, info: ItemInfo) -> ItemEntity:
         with self.get_session() as session:
            item = Item(
                name=info.name,
                price=info.price,
                deleted=info.deleted
            )
            session.add(item)
            session.flush()

            return ItemEntity(
                id=item.id,
                info=ItemInfo(
                    name=item.name,
                    price=float(item.price),
                    deleted=item.deleted
                )
            )

    def delete_cart(self, id: int) -> None:
        with self.get_session() as session:
            cart = session.get(Cart, id)
            if cart:
                session.execute(
                    delete(CartItemAssociation)
                    .where(CartItemAssociation.cart_id == id)
                )
                session.delete(cart)

    def delete_item(self, id: int) -> None:
        with self.get_session() as session:
            item = session.get(Item, id)
            if item:
                item.deleted = True

    def get_cart(self, id: int) -> CartEntity | None:
        with self.get_session() as session:
            cart = session.get(Cart, id)
            if not cart:
                return None
            
            cart_items = []
            total_price = 0
            
            for association in cart.cart_item_associations:
                item = association.item
                if not item.deleted:
                    cart_item_entity = CartItemEntity(
                        id=item.id,
                        info=CartItemInfo(
                            name=item.name,
                            quantity=association.quantity,
                            available=not item.deleted
                        )
                    )
                    cart_items.append(cart_item_entity)
                    total_price += item.price * association.quantity
            
            cart_info = CartInfo(
                items=cart_items,
                price=total_price
            )
            
            return CartEntity(id=cart.id, info=cart_info)

    def get_all_carts(self) -> List[CartEntity]:
        with self.get_session() as session:
            carts = session.execute(select(Cart)).scalars().all()
            result = []
            
            for cart in carts:
                cart_entity = self.get_cart(cart.id)
                if cart_entity:
                    result.append(cart_entity)
            
            return result

    def get_item(self, id: int) -> ItemEntity | None:
        with self.get_session() as session:
            item = session.get(Item, id)
            if not item:
                return None
            
            return ItemEntity(
                id=item.id,
                info=ItemInfo(
                    name=item.name,
                    price=item.price,
                    deleted=item.deleted
                )
            )

    def get_all_items(self) -> List[ItemEntity]:
        with self.get_session() as session:
            items = session.execute(select(Item)).scalars().all()
            return [
                ItemEntity(
                    id=item.id,
                    info=ItemInfo(
                        name=item.name,
                        price=item.price,
                        deleted=item.deleted
                    )
                )
                for item in items
            ]

    def add_item_to_cart(self, cart_id: int, item: ItemEntity) -> bool:
        with self.get_session() as session:
            cart = session.get(Cart, cart_id)
            if not cart:
                return False
            
            db_item = session.get(Item, item.id)
            if not db_item or db_item.deleted:
                return False
            
            existing_association = session.execute(
                select(CartItemAssociation)
                .where(
                    and_(
                        CartItemAssociation.cart_id == cart_id,
                        CartItemAssociation.item_id == item.id
                    )
                )
            ).scalar_one_or_none()
            
            if existing_association:
                existing_association.quantity += 1
            else:
                association = CartItemAssociation(
                    cart_id=cart_id,
                    item_id=item.id,
                    quantity=1
                )
                session.add(association)
            
            return True

    def put_item(self, item_id: int, request: PutItemRequest) -> ItemEntity | None:
        with self.get_session() as session:
            item = session.get(Item, item_id)
            if not item or item.deleted:
                return None
            
            item.name = request.name
            item.price = request.price
            
            return ItemEntity(
                id=item.id,
                info=ItemInfo(
                    name=item.name,
                    price=item.price,
                    deleted=item.deleted
                )
            )       

    class PatchResult(Enum):
        NotFound = 0
        NotModified = 1
        Unprocessable = 2

    def patch_item(self, item_id: int, patch_info: PatchItemInfo) -> ItemEntity | PatchResult: 
        with self.get_session() as session:
            item = session.get(Item, item_id)
            if not item:
                return self.PatchResult.NotFound
            
            if item.deleted:
                return self.PatchResult.NotModified
            
            modified = False
            
            if patch_info.name is not None and patch_info.name != item.name:
                item.name = patch_info.name
                modified = True
            
            if patch_info.price is not None:
                if patch_info.price < 0:
                    return self.PatchResult.Unprocessable
                if patch_info.price != item.price:
                    item.price = patch_info.price
                    modified = True
            
            if not modified:
                return self.PatchResult.NotModified
            
            return ItemEntity(
                id=item.id,
                info=ItemInfo(
                    name=item.name,
                    price=item.price,
                    deleted=item.deleted
                )
            )
