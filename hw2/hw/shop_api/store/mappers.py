from typing import Optional
from decimal import Decimal
from .models import (
    ItemInfo,
    ItemEntity,
    CartInfo,
    CartEntity,
    CartItemEntity,
)
from .database import (
    ItemOrm,
    CartOrm,
)


class ItemMapper:

    @staticmethod
    def to_domain(orm_item: ItemOrm) -> ItemEntity:
        """Convert ItemOrm → ItemEntity"""
        info = ItemInfo(
            name=orm_item.name,
            price=float(orm_item.price),  # Convert DECIMAL to float
            deleted=orm_item.deleted,
        )
        return ItemEntity(id=orm_item.id, info=info)

    @staticmethod
    def to_orm(
        info: ItemInfo,
        orm_item: Optional[ItemOrm] = None,
    ) -> ItemOrm:
        """Convert ItemInfo → ItemOrm (for create or update)"""
        if orm_item is None:
            orm_item = ItemOrm()

        orm_item.name = info.name
        orm_item.price = Decimal(str(info.price))  # Convert float to DECIMAL
        orm_item.deleted = info.deleted

        return orm_item


class CartMapper:

    @staticmethod
    def to_domain(orm_cart: CartOrm) -> CartEntity:
        """Convert CartOrm → CartEntity"""
        # Convert each CartItemOrm to CartItemEntity
        cart_item_entities = []
        for cart_item_orm in orm_cart.items:  # orm_cart.items is list of CartItemOrm
            cart_item_entity = CartItemEntity(
                item_id=cart_item_orm.item_id,
                item_name=cart_item_orm.item_name,
                quantity=cart_item_orm.quantity,
                available=cart_item_orm.available,
            )
            cart_item_entities.append(cart_item_entity)

        # Wrap in CartInfo
        info = CartInfo(items=cart_item_entities)

        # Wrap in CartEntity with ID
        return CartEntity(id=orm_cart.id, info=info)

    @staticmethod
    def to_orm(info: CartInfo, orm_cart: Optional[CartOrm] = None) -> CartOrm:
        """
        Convert CartInfo → CartOrm (rarely used)
        Most cart operations bypass this method.
        """
        if orm_cart is None:
            orm_cart = CartOrm()
        # Implementation not needed for basic cart operations
        return orm_cart
