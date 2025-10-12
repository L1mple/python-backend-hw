from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .schemas import ItemOut, CartItemView, CartView, ItemCreate, ItemPut, ItemPatch
from .models import Item, Cart, CartItem


# ---- Item helpers ----
async def create_item(session: AsyncSession, data: ItemCreate) -> ItemOut:
    item = Item(name=data.name, price=data.price, deleted=False)
    session.add(item)
    await session.flush()  # populate PK
    return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


async def get_item_or_404(session: AsyncSession, item_id: int) -> Item:
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if item is None or item.deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    return item


async def get_item_soft(session: AsyncSession, item_id: int) -> Optional[Item]:
    result = await session.execute(select(Item).where(Item.id == item_id))
    return result.scalar_one_or_none()


async def put_item(session: AsyncSession, item_id: int, data: ItemPut) -> ItemOut:
    item = await get_item_or_404(session, item_id)
    item.name = data.name
    item.price = data.price
    await session.flush()
    return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


async def patch_item(session: AsyncSession, item_id: int, data: ItemPatch) -> ItemOut:
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    if item.deleted:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED, detail="Item deleted"
        )

    if data.name is not None:
        item.name = data.name
    if data.price is not None:
        if data.price < 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid price",
            )
        item.price = data.price

    await session.flush()
    return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


async def delete_item(session: AsyncSession, item_id: int) -> dict:
    result = await session.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if item is not None:
        item.deleted = True
        await session.flush()
    return {"ok": True}


# ---- Cart helpers ----
async def cart_or_404(session: AsyncSession, cart_id: int) -> Cart:
    result = await session.execute(select(Cart).where(Cart.id == cart_id))
    cart = result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
        )
    return cart


async def create_cart(session: AsyncSession) -> int:
    cart = Cart()
    session.add(cart)
    await session.flush()
    return cart.id


async def add_to_cart(session: AsyncSession, cart_id: int, item_id: int) -> None:
    # Check cart and item exist (item must not be deleted)
    await cart_or_404(session, cart_id)
    await get_item_or_404(session, item_id)

    # Find existing link
    result = await session.execute(
        select(CartItem).where(CartItem.cart_id == cart_id, CartItem.item_id == item_id)
    )
    link = result.scalar_one_or_none()
    if link is None:
        link = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        session.add(link)
    else:
        link.quantity += 1
    await session.flush()


async def build_cart_view(session: AsyncSession, cart_id: int) -> CartView:
    cart = await cart_or_404(session, cart_id)

    # Load links with joined items
    result = await session.execute(
        select(CartItem, Item)
        .join(Item, CartItem.item_id == Item.id)
        .where(CartItem.cart_id == cart.id)
    )
    rows = result.all()

    items = []
    total = 0.0
    for link, item in rows:
        name = item.name
        available = not item.deleted
        items.append(
            CartItemView(
                id=item.id, name=name, quantity=link.quantity, available=available
            )
        )
        if available:
            total += item.price * link.quantity

    return CartView(id=cart.id, items=items, price=total)
