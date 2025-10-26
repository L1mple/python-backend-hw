from __future__ import annotations

from typing import List, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from shop_api.core.db import SessionLocal
from shop_api.core.models import Item as ItemORM, Cart as CartORM, CartItem as CartItemORM
from shop_api.core.schemas import (
    CartItemView,
    CartView,
    ItemCreate,
    ItemOut,
    ItemPatch,
    ItemPut,
)


@asynccontextmanager
async def _session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session


async def get_item_or_404(item_id: int) -> ItemOut:
    async with _session() as s:
        result = await s.execute(select(ItemORM).where(ItemORM.id == item_id))
        item = result.scalar_one_or_none()
        if item is None or item.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


async def get_item_soft(item_id: int) -> Optional[ItemORM]:
    async with _session() as s:
        stmt = select(ItemORM).where(ItemORM.id == item_id)
        result = await s.execute(stmt)
        return result.scalar_one_or_none()


async def list_items(offset: int = 0, limit: int = 10, min_price: Optional[float] = None, max_price: Optional[float] = None, show_deleted: bool = False) -> List[ItemOut]:
    async with _session() as s:
        query = select(ItemORM)
        if not show_deleted:
            query = query.where(ItemORM.deleted == False)  # noqa: E712
        if min_price is not None:
            query = query.where(ItemORM.price >= min_price)
        if max_price is not None:
            query = query.where(ItemORM.price <= max_price)
        result = await s.execute(query.offset(offset).limit(limit))
        rows = result.scalars().all()
        return [ItemOut(id=r.id, name=r.name, price=r.price, deleted=r.deleted) for r in rows]


async def create_item(data: ItemCreate) -> ItemOut:
    async with _session() as s:
        item = ItemORM(name=data.name, price=data.price, deleted=False)
        s.add(item)
        await s.commit()
        await s.refresh(item)
        return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


async def put_item(item_id: int, data: ItemPut) -> ItemOut:
    async with _session() as s:
        result = await s.execute(select(ItemORM).where(ItemORM.id == item_id))
        item = result.scalar_one_or_none()
        if item is None or item.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        item.name = data.name
        item.price = data.price
        await s.commit()
        await s.refresh(item)
        return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


async def patch_item(item_id: int, data: ItemPatch) -> ItemOut:
    async with _session() as s:
        result = await s.execute(select(ItemORM).where(ItemORM.id == item_id))
        item = result.scalar_one_or_none()
        if item is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
        if item.deleted:
            raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Item deleted")

        if data.name is not None:
            item.name = data.name
        if data.price is not None:
            if data.price < 0:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid price")
            item.price = data.price
        await s.commit()
        await s.refresh(item)
        return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


async def delete_item(item_id: int) -> dict:
    async with _session() as s:
        result = await s.execute(select(ItemORM).where(ItemORM.id == item_id))
        item = result.scalar_one_or_none()
        if item is not None:
            item.deleted = True
            await s.commit()
    return {"ok": True}


async def create_cart() -> int:
    async with _session() as s:
        c = CartORM()
        s.add(c)
        await s.commit()
        await s.refresh(c)
        return c.id


async def cart_or_404(cart_id: int) -> CartORM:
    async with _session() as s:
        result = await s.execute(select(CartORM).where(CartORM.id == cart_id))
        cart = result.scalar_one_or_none()
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
        return cart


async def build_cart_view(cart_id: int) -> CartView:
    async with _session() as s:
        result = await s.execute(
            select(CartORM)
            .where(CartORM.id == cart_id)
            .options(selectinload(CartORM.items))
        )
        cart = result.scalar_one_or_none()
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        item_ids = [ci.item_id for ci in cart.items]
        if item_ids:
            items_result = await s.execute(select(ItemORM).where(ItemORM.id.in_(item_ids)))
            items_by_id = {i.id: i for i in items_result.scalars().all()}
        else:
            items_by_id = {}

        cart_items: List[CartItemView] = []
        total = 0.0
        for ci in cart.items:
            item = items_by_id.get(ci.item_id)
            name = item.name if item else f"item:{ci.item_id}"
            available = bool(item and not item.deleted)
            cart_items.append(CartItemView(id=ci.item_id, name=name, quantity=ci.quantity, available=available))
            if available:
                total += item.price * ci.quantity

        return CartView(id=cart_id, items=cart_items, price=total)


async def list_carts(offset: int = 0, limit: int = 10, min_price: Optional[float] = None, max_price: Optional[float] = None, min_quantity: Optional[int] = None, max_quantity: Optional[int] = None) -> List[CartView]:
    async with _session() as s:
        result = await s.execute(
            select(CartORM)
            .options(selectinload(CartORM.items))
        )
        carts = result.scalars().all()

        all_item_ids = {item.item_id for cart in carts for item in cart.items}

        if all_item_ids:
            items_result = await s.execute(select(ItemORM).where(ItemORM.id.in_(all_item_ids)))
            items_by_id = {i.id: i for i in items_result.scalars().all()}
        else:
            items_by_id = {}

        views: List[CartView] = []
        for cart in carts:
            items: List[CartItemView] = []
            total = 0.0
            for ci in cart.items:
                item = items_by_id.get(ci.item_id)
                name = item.name if item else f"item:{ci.item_id}"
                available = bool(item and not item.deleted)
                items.append(CartItemView(id=ci.item_id, name=name, quantity=ci.quantity, available=available))
                if available:
                    total += item.price * ci.quantity

            cart_view = CartView(id=cart.id, items=items, price=total)

            if not all(
                [
                    min_price is None or cart_view.price >= min_price,
                    max_price is None or cart_view.price <= max_price,
                    min_quantity is None or sum(i.quantity for i in cart_view.items) >= min_quantity,
                    max_quantity is None or sum(i.quantity for i in cart_view.items) <= max_quantity,
                ]
            ):
                continue

            views.append(cart_view)

        return views[offset : offset + limit]


async def add_to_cart(cart_id: int, item_id: int) -> dict:
    async with _session() as s:
        cart_result = await s.execute(select(CartORM).where(CartORM.id == cart_id))
        cart = cart_result.scalar_one_or_none()
        if cart is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        item_result = await s.execute(select(ItemORM).where(ItemORM.id == item_id))
        item = item_result.scalar_one_or_none()
        if item is None or item.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        cart_item_result = await s.execute(
            select(CartItemORM).where(
                CartItemORM.cart_id == cart_id,
                CartItemORM.item_id == item_id
            )
        )
        ci = cart_item_result.scalar_one_or_none()
        if ci is None:
            ci = CartItemORM(cart_id=cart_id, item_id=item_id, quantity=1)
            s.add(ci)
        else:
            ci.quantity = ci.quantity + 1
        await s.commit()
    return {"ok": True}
