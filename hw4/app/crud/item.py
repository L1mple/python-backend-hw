from pymongo import DESCENDING, ReturnDocument

from app.schemas.item import CreateItem, Item, PatchItem, UpdateItem


async def _get_next_id(mongo) -> int:
    """Берёт последний id из коллекции и возвращает следующий."""
    collection = mongo.mongo["items"]
    last_doc = await collection.find_one(sort=[("id", DESCENDING)])
    if last_doc and "id" in last_doc:
        return int(last_doc["id"]) + 1
    return 1


async def create_item(mongo, item: CreateItem) -> Item:
    """Создаёт новый элемент и возвращает Item (Pydantic-модель)."""
    collection = mongo.mongo["items"]
    new_id = await _get_next_id(mongo)
    new_item = Item(id=new_id, name=item.name, price=item.price)
    await collection.insert_one(new_item.model_dump())
    return new_item


async def get_item_by_id(mongo, item_id: int) -> Item | None:
    """
    Возвращает элемент по id в виде Pydantic-схемы Item.
    Игнорирует элементы с deleted=True.
    """
    collection = mongo.mongo["items"]
    doc = await collection.find_one({"id": item_id, "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]})

    if not doc:
        return None

    # Преобразуем документ Mongo в Pydantic модель
    return Item(**doc)


async def update_item(mongo, item_id: int, item: UpdateItem) -> Item | None:
    """
    Обновляет существующий элемент по id.
    Возвращает обновлённую Pydantic-модель Item или None, если элемента нет.
    """
    collection = mongo.mongo["items"]

    # Подготовка полей для обновления
    update_data = {
        "name": item.name,
        "price": item.price,
        "deleted": item.deleted if item.deleted is not None else False,
    }

    # Находим и обновляем документ атомарно
    updated_doc = await collection.find_one_and_update(
        {"id": item_id}, {"$set": update_data}, return_document=ReturnDocument.AFTER
    )

    if not updated_doc:
        return None

    return Item(**updated_doc)


async def patch_item(mongo, item_id: int, item: PatchItem) -> tuple[Item | None, int]:
    """
    Патч элемента по id.
    Возвращает (Item, status_code):
    - 200: элемент обновлён
    - 304: изменений нет
    - 404: элемент не найден
    """
    collection = mongo.mongo["items"]

    # Получаем текущий документ
    current_doc = await collection.find_one({"id": item_id})
    if not current_doc or current_doc.get("deleted", False):
        return None, 404

    # Проверяем, есть ли реальные изменения
    if (item.name is None or item.name == current_doc["name"]) and (
        item.price is None or item.price == current_doc["price"]
    ):
        return Item(**current_doc), 304

    # Подготавливаем поля для обновления
    update_data = {}
    if item.name is not None:
        update_data["name"] = item.name
    if item.price is not None:
        update_data["price"] = item.price

    # Обновляем документ
    updated_doc = await collection.find_one_and_update(
        {"id": item_id}, {"$set": update_data}, return_document=ReturnDocument.AFTER
    )

    return Item(**updated_doc), 200


async def delete_item(mongo, item_id: int) -> Item | None:
    """
    Soft delete элемента по id.
    Возвращает Pydantic-модель Item или None, если элемент не найден.
    """
    collection = mongo.mongo["items"]

    # Находим и обновляем документ, устанавливая deleted=True
    deleted_doc = await collection.find_one_and_update(
        {"id": item_id}, {"$set": {"deleted": True}}, return_document=ReturnDocument.AFTER
    )

    if not deleted_doc:
        return None

    return Item(**deleted_doc)


async def get_items(
    mongo,
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> tuple[list[Item] | None, int]:
    """
    Получение списка элементов с фильтрацией, пагинацией и опцией show_deleted.
    Возвращает (list[Item], status_code)
    """
    # Валидация входных параметров
    if offset is not None and offset < 0:
        return None, 422
    if limit is not None and limit <= 0:
        return None, 422
    if min_price is not None and min_price < 0:
        return None, 422
    if max_price is not None and max_price < 0:
        return None, 422

    collection = mongo.mongo["items"]

    # Формируем фильтр для Mongo
    filter_query = {}
    if not show_deleted:
        filter_query["$or"] = [{"deleted": {"$exists": False}}, {"deleted": False}]
    if min_price is not None:
        filter_query["price"] = filter_query.get("price", {})
        filter_query["price"]["$gte"] = min_price
    if max_price is not None:
        filter_query["price"] = filter_query.get("price", {})
        filter_query["price"]["$lte"] = max_price

    # Получаем документы с сортировкой по id и пагинацией
    cursor = collection.find(filter_query).sort("id", 1).skip(offset).limit(limit)
    items = [Item(**doc) async for doc in cursor]

    return items, 200