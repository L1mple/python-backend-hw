from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import joinedload

from .base import CRUDBase
from ..models import CartModel, CartItemModel, ItemModel
from ..schemas import CartItemResponse, CartResponse


class CRUDCart(CRUDBase[CartModel, None]):

    async def get_carts_with_filters(
            self,
            db: AsyncSession,
            offset: int = 0,
            limit: int = 10,
            min_price: Optional[float] = None,
            max_price: Optional[float] = None,
            min_quantity: Optional[int] = None,
            max_quantity: Optional[int] = None,
    ) -> List[CartResponse]:

        quantity_subq = (
            select(
                CartItemModel.cart_id,
                func.coalesce(func.sum(CartItemModel.quantity), 0).label("total_quantity")
            )
            .join(ItemModel, CartItemModel.item_id == ItemModel.id)
            .where(ItemModel.deleted.is_(False))
            .group_by(CartItemModel.cart_id)
            .subquery()
        )

        query = (
            select(
                CartModel.id,
                CartModel.price,
                func.coalesce(quantity_subq.c.total_quantity, 0).label("total_quantity")
            )
            .select_from(CartModel)
            .outerjoin(quantity_subq, CartModel.id == quantity_subq.c.cart_id)
        )

        if min_price is not None:
            query = query.where(CartModel.price >= min_price)
        if max_price is not None:
            query = query.where(CartModel.price <= max_price)
        if min_quantity is not None:
            query = query.where(func.coalesce(quantity_subq.c.total_quantity, 0) >= min_quantity)
        if max_quantity is not None:
            query = query.where(func.coalesce(quantity_subq.c.total_quantity, 0) <= max_quantity)

        query = query.offset(offset).limit(limit)

        result = await db.execute(query)
        cart_rows = result.fetchall()

        if not cart_rows:
            return []

        cart_ids = [r.id for r in cart_rows]
        cart_info = {r.id: r for r in cart_rows}

        cart_items_result = await db.execute(
            select(CartItemModel)
            .options(joinedload(CartItemModel.item))
            .join(ItemModel, CartItemModel.item_id == ItemModel.id)
            .where(CartItemModel.cart_id.in_(cart_ids))
            .where(ItemModel.deleted.is_(False))
        )
        cart_items = cart_items_result.scalars().all()

        cart_items_map = {}
        for ci in cart_items:
            cart_items_map.setdefault(ci.cart_id, []).append(ci)

        response = []
        for cart_id in cart_ids:
            row = cart_info[cart_id]
            total_quantity = row.total_quantity
            items = []
            if total_quantity > 0:
                items = [
                    CartItemResponse(
                        id=ci.item_id,
                        name=ci.item.name,
                        quantity=ci.quantity,
                        available=ci.available,
                    )
                    for ci in cart_items_map.get(cart_id, [])
                ]
            response.append(
                CartResponse(
                    id=cart_id,
                    items=items,
                    price=row.price
                )
            )
        return response


    async def add_item_to_cart(
            self,
            db: AsyncSession,
            *,
            cart_id: UUID,
            item_id: UUID,
    ) -> bool:

        cart_result = await db.execute(
            select(CartModel)
            .where(CartModel.id == cart_id)
            .with_for_update()
        )
        cart = cart_result.scalar_one_or_none()
        if not cart:
            return False

        item_result = await db.execute(
            select(ItemModel)
            .where(ItemModel.id == item_id)
            .where(ItemModel.deleted.is_(False))
        )
        item = item_result.scalar_one_or_none()
        if not item:
            return False

        cart_item_result = await db.execute(
            select(CartItemModel)
            .where(CartItemModel.cart_id == cart_id)
            .where(CartItemModel.item_id == item_id)
        )
        existing_cart_item = cart_item_result.scalar_one_or_none()

        if existing_cart_item:
            existing_cart_item.quantity += 1
            price_delta = item.price
        else:
            new_cart_item = CartItemModel(
                cart_id=cart_id,
                item_id=item_id,
                quantity=1,
                available=True
            )
            db.add(new_cart_item)
            price_delta = item.price

        cart.price += price_delta

        try:
            await db.commit()
            return True
        except Exception:
            await db.rollback()
            return False


    async def get_cart_with_items(
            self,
            db: AsyncSession,
            *,
            id: UUID,
    ):
        cart = await db.get(CartModel, id)
        if not cart:
            return None

        await db.refresh(cart, ["items"])

        items = []
        total_quantity = 0
        for ci in cart.items:
            if ci.item.deleted:
                continue
            items.append(
                CartItemResponse(
                    id=ci.item_id,
                    name=ci.item.name,
                    quantity=ci.quantity,
                    available=ci.available,
                )
            )
            total_quantity += ci.quantity

        return CartResponse(
            id=cart.id,
            items=items,
            price=cart.price
        )



crud_cart = CRUDCart(CartModel)