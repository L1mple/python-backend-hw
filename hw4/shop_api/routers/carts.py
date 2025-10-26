from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional

from shop_api.database import get_session
from shop_api.models.cart import Cart, CartItem
from shop_api.models.item import Item
from shop_api.schemas.cart import CartOut, CartItemOut
from shop_api.metrics import carts_created_counter

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/", status_code=201)
async def create_cart(session: AsyncSession = Depends(get_session)):
    cart = Cart()
    session.add(cart)
    await session.commit()
    await session.refresh(cart)

    carts_created_counter.inc()
    return {"id": cart.id}


@router.post("/{cart_id}/add/{item_id}", status_code=200)
async def add_item_to_cart(cart_id: int, item_id: int, session: AsyncSession = Depends(get_session)):
    cart = await session.get(Cart, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    item = await session.get(Item, item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")

    result = await session.execute(
        select(CartItem).where(CartItem.cart_id == cart_id, CartItem.item_id == item_id)
    )
    cart_item = result.scalar_one_or_none()

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        session.add(cart_item)

    await session.commit()
    return {"status": "ok"}


@router.get("/{cart_id}", response_model=CartOut)
async def get_cart(cart_id: int, session: AsyncSession = Depends(get_session)):
    cart = await session.get(Cart, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    result = await session.execute(
        select(CartItem, Item)
        .join(Item, CartItem.item_id == Item.id)
        .where(CartItem.cart_id == cart_id)
    )

    cart_items = []
    total_price = 0.0
    for cart_item, item in result.all():
        cart_items.append(
            CartItemOut(
                id=item.id,
                name=item.name,
                quantity=cart_item.quantity,
                available=not item.deleted,
            )
        )
        if not item.deleted:
            total_price += item.price * cart_item.quantity

    cart.price = total_price
    await session.commit()

    return CartOut(id=cart.id, items=cart_items, price=total_price)
