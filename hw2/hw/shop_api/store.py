from typing import List, Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .db_models import Cart, CartItemAssociation, Item
from .models import CartEntity, CartItem, ItemEntity, ItemInfo, PatchItemInfo


async def add_item(session: AsyncSession, info: ItemInfo) -> ItemEntity:
    db_item = Item(name=info.name, price=info.price, deleted=info.deleted)
    session.add(db_item)
    await session.commit()
    await session.refresh(db_item)
    return ItemEntity(id=db_item.id, info=ItemInfo(
        name=db_item.name,
        price=db_item.price,
        deleted=db_item.deleted
    ))

async def get_item(session: AsyncSession, item_id: int) -> Optional[ItemEntity]:
    result = await session.execute(select(Item).where(Item.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        return None
    return ItemEntity(id=db_item.id, info=ItemInfo(
        name=db_item.name,
        price=db_item.price,
        deleted=db_item.deleted
    ))

async def get_items_filtered(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
) -> List[ItemEntity]:
    query = select(Item)

    if not show_deleted:
        query = query.where(Item.deleted == False)
    
    if min_price is not None:
        query = query.where(Item.price >= min_price)
    if max_price is not None:
        query = query.where(Item.price <= max_price)
    
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    db_items = result.scalars().all()
    
    return [
        ItemEntity(id=db_item.id, info=ItemInfo(
            name=db_item.name,
            price=db_item.price,
            deleted=db_item.deleted
        ))
        for db_item in db_items
    ]

async def update_item(
    session: AsyncSession,
    item_id: int,
    info: ItemInfo
) -> Optional[ItemEntity]:
    result = await session.execute(select(Item).where(Item.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        return None
    db_item.name = info.name
    db_item.price = info.price
    db_item.deleted = info.deleted
    await session.commit()
    await session.refresh(db_item)
    return ItemEntity(id=db_item.id, info=ItemInfo(
        name=db_item.name,
        price=db_item.price,
        deleted=db_item.deleted
    ))

async def patch_item(
    session: AsyncSession,
    item_id: int,
    patch_info: PatchItemInfo
) -> Optional[ItemEntity]:
    result = await session.execute(select(Item).where(Item.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        return None
    if patch_info.name is not None:
        db_item.name = patch_info.name
    if patch_info.price is not None:
        db_item.price = patch_info.price
    if patch_info.deleted is not None:
        db_item.deleted = patch_info.deleted
    await session.commit()
    await session.refresh(db_item)
    return ItemEntity(id=db_item.id, info=ItemInfo(
        name=db_item.name,
        price=db_item.price,
        deleted=db_item.deleted
    ))

async def delete_item(session: AsyncSession, item_id: int) -> bool:
    result = await session.execute(select(Item).where(Item.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item:
        return False
    db_item.deleted = True
    result = await session.execute(
        select(Cart)
        .where(Cart.id.in_(
            select(CartItemAssociation.cart_id).where(CartItemAssociation.item_id == item_id)
        ))
        .options(selectinload(Cart.cart_items).selectinload(CartItemAssociation.item))
    )
    affected_carts = result.scalars().all()
    for cart in affected_carts:
        await _recalculate_cart_price(session, cart)
    await session.commit()
    return True

async def add_cart(session: AsyncSession) -> CartEntity:
    db_cart = Cart(price=0.0)
    session.add(db_cart)
    await session.commit()
    await session.refresh(db_cart)
    return CartEntity(id=db_cart.id, items=[], price=0.0)

async def get_cart(session: AsyncSession, cart_id: int) -> Optional[CartEntity]:
    result = await session.execute(
        select(Cart)
        .where(Cart.id == cart_id)
        .options(selectinload(Cart.cart_items).selectinload(CartItemAssociation.item))
    )
    db_cart = result.scalar_one_or_none()
    if not db_cart:
        return None
    cart_items = []
    for assoc in db_cart.cart_items:
        cart_items.append(CartItem(
            id=assoc.item_id,
            name=assoc.item.name,
            quantity=assoc.quantity,
            available=not assoc.item.deleted
        ))
    return CartEntity(
        id=db_cart.id,
        items=cart_items,
        price=db_cart.price
    )

async def get_carts_filtered(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
) -> List[CartEntity]:
    query = select(Cart).options(
        selectinload(Cart.cart_items).selectinload(CartItemAssociation.item)
    )
    if min_price is not None:
        query = query.where(Cart.price >= min_price)
    if max_price is not None:
        query = query.where(Cart.price <= max_price)
    result = await session.execute(query)
    db_carts = result.scalars().all()
    cart_entities = []
    for db_cart in db_carts:
        cart_items = []
        total_quantity = 0
        for assoc in db_cart.cart_items:
            cart_items.append(CartItem(
                id=assoc.item_id,
                name=assoc.item.name,
                quantity=assoc.quantity,
                available=not assoc.item.deleted
            ))
            total_quantity += assoc.quantity
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        cart_entities.append(CartEntity(
            id=db_cart.id,
            items=cart_items,
            price=db_cart.price
        ))
    return cart_entities[offset:offset + limit]


async def add_item_to_cart(
    session: AsyncSession,
    cart_id: int,
    item_id: int
) -> Optional[CartEntity]:
    result = await session.execute(
        select(Cart)
        .where(Cart.id == cart_id)
        .options(selectinload(Cart.cart_items).selectinload(CartItemAssociation.item))
    )
    db_cart = result.scalar_one_or_none()
    if not db_cart:
        return None
    result = await session.execute(select(Item).where(Item.id == item_id))
    db_item = result.scalar_one_or_none()
    if not db_item or db_item.deleted:
        return None
    existing_assoc = None
    for assoc in db_cart.cart_items:
        if assoc.item_id == item_id:
            existing_assoc = assoc
            break
    if existing_assoc:
        existing_assoc.quantity += 1
    else:
        new_assoc = CartItemAssociation(
            cart_id=cart_id,
            item_id=item_id,
            quantity=1,
            item=db_item
        )
        session.add(new_assoc)
        db_cart.cart_items.append(new_assoc)
    await _recalculate_cart_price(session, db_cart)
    await session.commit()
    result = await session.execute(
        select(Cart)
        .where(Cart.id == cart_id)
        .options(selectinload(Cart.cart_items).selectinload(CartItemAssociation.item))
    )
    db_cart = result.scalar_one_or_none()
    if not db_cart:
        return None
    cart_items = []
    for assoc in db_cart.cart_items:
        cart_items.append(CartItem(
            id=assoc.item_id,
            name=assoc.item.name,
            quantity=assoc.quantity,
            available=not assoc.item.deleted
        ))
    return CartEntity(
        id=db_cart.id,
        items=cart_items,
        price=db_cart.price
    )


async def _recalculate_cart_price(session: AsyncSession, cart: Cart) -> None:
    total_price = 0.0
    
    for assoc in cart.cart_items:
        if not assoc.item.deleted:
            total_price += assoc.item.price * assoc.quantity
    
    cart.price = total_price