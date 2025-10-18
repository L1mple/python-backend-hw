from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ItemInfo, ItemEntity, PatchItemInfo
from .db_models import ItemDB


async def add(session: AsyncSession, info: ItemInfo) -> ItemEntity:
    """Create new item"""
    item_db = ItemDB(name=info.name, price=info.price, deleted=info.deleted)

    session.add(item_db)  # добавляем в сессию и сохранение
    await session.flush()  # получаем ID без commit

    return ItemEntity(id=item_db.id, info=info)


async def delete(session: AsyncSession, id: int) -> ItemEntity | None:
    """Marks item as deleted"""

    result = await session.execute(
        select(ItemDB).where(ItemDB.id == id)
    )  # получаем товар из БД
    item_db = result.scalar_one_or_none()  # получаем одну запись

    if item_db is None:
        return None

    item_db.deleted = True
    await session.flush()

    return ItemEntity(
        id=item_db.id,
        info=ItemInfo(name=item_db.name, price=item_db.price, deleted=item_db.deleted),
    )


async def get_one(session: AsyncSession, id: int) -> ItemEntity | None:
    """Get item by ID"""
    result = await session.execute(select(ItemDB).where(ItemDB.id == id))
    item_db = result.scalar_one_or_none()

    if item_db is None:
        return None

    return ItemEntity(
        id=item_db.id,
        info=ItemInfo(name=item_db.name, price=item_db.price, deleted=item_db.deleted),
    )


async def get_many(
    session: AsyncSession,
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> list[ItemEntity]:
    """Get many items by query params"""

    query = select(ItemDB)

    # Фильтры
    if not show_deleted:
        query = query.where(ItemDB.deleted == False)

    if min_price is not None:
        query = query.where(ItemDB.price >= min_price)

    if max_price is not None:
        query = query.where(ItemDB.price <= max_price)

    # Пагинация
    query = query.offset(offset).limit(limit)

    # Выполнение запроса
    result = await session.execute(query)
    items_db = result.scalars().all()

    return [
        ItemEntity(
            id=item_db.id,
            info=ItemInfo(
                name=item_db.name, price=item_db.price, deleted=item_db.deleted
            ),
        )
        for item_db in items_db
    ]


async def update(session: AsyncSession, id: int, info: ItemInfo) -> ItemEntity | None:
    """Update item by ID"""
    result = await session.execute(select(ItemDB).where(ItemDB.id == id))
    item_db = result.scalar_one_or_none()

    if item_db is None:
        return None

    item_db.name = info.name
    item_db.price = info.price
    item_db.deleted = info.deleted

    await session.flush()

    return ItemEntity(id=item_db.id, info=info)


async def upsert(session: AsyncSession, id: int, info: ItemInfo) -> ItemEntity:
    """Upsert item by ID"""
    result = await session.execute(select(ItemDB).where(ItemDB.id == id))
    item_db = result.scalar_one_or_none()

    if item_db is None:
        # Создание нового товара с заданным ID
        item_db = ItemDB(id=id, name=info.name, price=info.price, deleted=info.deleted)
        session.add(item_db)
    else:
        # Обновление существующего товара
        item_db.name = info.name
        item_db.price = info.price
        item_db.deleted = info.deleted

    await session.flush()

    return ItemEntity(id=item_db.id, info=info)


async def patch(
    session: AsyncSession, id: int, patch_info: PatchItemInfo
) -> ItemEntity | None:
    """Patch item by ID"""
    result = await session.execute(select(ItemDB).where(ItemDB.id == id))
    item_db = result.scalar_one_or_none()

    if item_db is None:
        return None

    # Обновление только указанных полей
    if patch_info.name is not None:
        item_db.name = patch_info.name

    if patch_info.price is not None:
        item_db.price = patch_info.price

    if patch_info.deleted is not None:
        item_db.deleted = patch_info.deleted

    await session.flush()

    return ItemEntity(
        id=item_db.id,
        info=ItemInfo(name=item_db.name, price=item_db.price, deleted=item_db.deleted),
    )
