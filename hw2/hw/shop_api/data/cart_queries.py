from sqlalchemy import select, delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from .models import CartInfo, CartItemInfo, CartEntity, PatchCartInfo
from .db_models import CartDB, ItemDB, cart_items_table


async def add(session: AsyncSession, info: CartInfo) -> CartEntity:
    """Create new cart with items."""
    cart_db = CartDB(price=info.price)
    session.add(cart_db)
    await session.flush()

    # Добавление товаров в корзину
    for item_info in info.items:
        result = await session.execute(select(ItemDB).where(ItemDB.id == item_info.id))
        item_db = result.scalar_one_or_none()

        if item_db:
            # Добавление связи через промежуточную таблицу
            await session.execute(
                cart_items_table.insert().values(
                    cart_id=cart_db.id, item_id=item_db.id, quantity=item_info.quantity
                )
            )

    await session.flush()

    # Пересчитывание цены корзины
    cart_db.price = await _calculate_price(session, cart_db.id)
    await session.flush()

    return await get_one(session, cart_db.id)


async def delete(session: AsyncSession, id: int) -> None:
    """Delete cart by ID."""
    await session.execute(sql_delete(CartDB).where(CartDB.id == id))
    await session.flush()


async def get_one(session: AsyncSession, id: int) -> CartEntity | None:
    """Get cart by ID."""
    result = await session.execute(select(CartDB).where(CartDB.id == id))
    cart_db = result.scalar_one_or_none()

    if cart_db is None:
        return None

    # Получение товаров из корзины
    items_query = (
        select(ItemDB.id, ItemDB.name, ItemDB.deleted, cart_items_table.c.quantity)
        .join(cart_items_table, ItemDB.id == cart_items_table.c.item_id)
        .where(cart_items_table.c.cart_id == cart_db.id)
    )

    result = await session.execute(items_query)
    items_data = result.all()

    cart_items = [
        CartItemInfo(id=item_id, name=name, quantity=quantity, available=not deleted)
        for item_id, name, deleted, quantity in items_data
    ]

    return CartEntity(
        id=cart_db.id, info=CartInfo(items=cart_items, price=cart_db.price)
    )


async def get_many(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> list[CartEntity]:
    """Get many carts by query params."""

    query = select(CartDB)

    # Фильтры по цене
    if min_price is not None:
        query = query.where(CartDB.price >= min_price)

    if max_price is not None:
        query = query.where(CartDB.price <= max_price)

    # Пагинация
    query = query.offset(offset).limit(limit)

    result = await session.execute(query)
    carts_db = result.scalars().all()

    carts = []
    for cart_db in carts_db:
        cart_entity = await get_one(session, cart_db.id)
        if cart_entity is None:
            continue

        # Фильтр по общему количеству товаров
        total_quantity = sum(item.quantity for item in cart_entity.info.items)

        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        carts.append(cart_entity)

    return carts


async def update(session: AsyncSession, id: int, info: CartInfo) -> CartEntity | None:
    """Update cart by ID"""
    result = await session.execute(select(CartDB).where(CartDB.id == id))
    cart_db = result.scalar_one_or_none()

    if cart_db is None:
        return None

    # Удаление старых связей с товарами
    await session.execute(
        sql_delete(cart_items_table).where(cart_items_table.c.cart_id == id)
    )

    # Добавление новых товаров
    for item_info in info.items:
        result = await session.execute(select(ItemDB).where(ItemDB.id == item_info.id))
        item_db = result.scalar_one_or_none()

        if item_db:
            await session.execute(
                cart_items_table.insert().values(
                    cart_id=cart_db.id, item_id=item_db.id, quantity=item_info.quantity
                )
            )

    # Пересчитываем цену
    cart_db.price = await _calculate_price(session, cart_db.id)
    await session.flush()

    return await get_one(session, cart_db.id)


async def upsert(session: AsyncSession, id: int, info: CartInfo) -> CartEntity:
    """Upsert cart by ID"""
    result = await session.execute(select(CartDB).where(CartDB.id == id))
    cart_db = result.scalar_one_or_none()

    if cart_db is None:

        cart_db = CartDB(id=id, price=0.0)
        session.add(cart_db)
        await session.flush()

    await session.execute(
        sql_delete(cart_items_table).where(cart_items_table.c.cart_id == id)
    )

    for item_info in info.items:
        result = await session.execute(select(ItemDB).where(ItemDB.id == item_info.id))
        item_db = result.scalar_one_or_none()

        if item_db:
            await session.execute(
                cart_items_table.insert().values(
                    cart_id=cart_db.id, item_id=item_db.id, quantity=item_info.quantity
                )
            )

    cart_db.price = await _calculate_price(session, cart_db.id)
    await session.flush()

    return await get_one(session, cart_db.id)


async def patch(
    session: AsyncSession, id: int, patch_info: PatchCartInfo
) -> CartEntity | None:
    """Patch cart by ID"""
    result = await session.execute(select(CartDB).where(CartDB.id == id))
    cart_db = result.scalar_one_or_none()

    if cart_db is None:
        return None

    if patch_info.items is not None:

        await session.execute(
            sql_delete(cart_items_table).where(cart_items_table.c.cart_id == id)
        )

        for item_info in patch_info.items:
            result = await session.execute(
                select(ItemDB).where(ItemDB.id == item_info.id)
            )
            item_db = result.scalar_one_or_none()

            if item_db:
                await session.execute(
                    cart_items_table.insert().values(
                        cart_id=cart_db.id,
                        item_id=item_db.id,
                        quantity=item_info.quantity,
                    )
                )

        cart_db.price = await _calculate_price(session, cart_db.id)

    await session.flush()
    return await get_one(session, cart_db.id)


async def _calculate_price(session: AsyncSession, cart_id: int) -> float:
    """Calculate cart price"""
    query = (
        select(ItemDB.price, cart_items_table.c.quantity)
        .join(cart_items_table, ItemDB.id == cart_items_table.c.item_id)
        .where(cart_items_table.c.cart_id == cart_id)
    )

    result = await session.execute(query)
    items = result.all()

    total = sum(price * quantity for price, quantity in items)
    return total


async def add_item_to_cart(
    session: AsyncSession, cart_id: int, product_id: int, quantity: int
) -> CartEntity | None:
    """Add item to cart"""
    # Проверка существования корзины
    result = await session.execute(select(CartDB).where(CartDB.id == cart_id))
    cart_db = result.scalar_one_or_none()

    if cart_db is None:
        return None

    # Проверка существования товара
    result = await session.execute(select(ItemDB).where(ItemDB.id == product_id))
    product_db = result.scalar_one_or_none()

    if product_db is None:
        return None

    # Проверка наличия товара в корзине
    result = await session.execute(
        select(cart_items_table.c.quantity).where(
            cart_items_table.c.cart_id == cart_id,
            cart_items_table.c.item_id == product_id,
        )
    )
    existing_quantity = result.scalar_one_or_none()

    if existing_quantity is not None:
        # Обновление количества существующего товара
        await session.execute(
            cart_items_table.update()
            .where(
                cart_items_table.c.cart_id == cart_id,
                cart_items_table.c.item_id == product_id,
            )
            .values(quantity=existing_quantity + quantity)
        )
    else:
        # Добавлением нового товара
        await session.execute(
            cart_items_table.insert().values(
                cart_id=cart_id, item_id=product_id, quantity=quantity
            )
        )

    cart_db.price = await _calculate_price(session, cart_id)
    await session.flush()

    return await get_one(session, cart_id)


async def remove_item_from_cart(
    session: AsyncSession, cart_id: int, product_id: int
) -> CartEntity | None:
    """Delete item from cart"""

    result = await session.execute(select(CartDB).where(CartDB.id == cart_id))
    cart_db = result.scalar_one_or_none()

    if cart_db is None:
        return None

    result = await session.execute(
        sql_delete(cart_items_table).where(
            cart_items_table.c.cart_id == cart_id,
            cart_items_table.c.item_id == product_id,
        )
    )

    if result.rowcount == 0:
        return None

    cart_db.price = await _calculate_price(session, cart_id)
    await session.flush()

    return await get_one(session, cart_id)
