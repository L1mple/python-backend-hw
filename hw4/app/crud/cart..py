from pymongo import DESCENDING, ReturnDocument

from app.schemas.cart import Cart, ItemCart
from app.schemas.item import CreateItem, Item, PatchItem, UpdateItem


async def create_cart(mongo) -> Cart:
    """
    Создаёт новую корзину с уникальным id и пустым списком items.
    """
    collection = mongo.mongo["carts"]

    # Генерация id на основе последнего документа
    last_cart = await collection.find_one(sort=[("id", DESCENDING)])
    new_id = last_cart["id"] + 1 if last_cart and "id" in last_cart else 1

    # Создаём Pydantic объект
    new_cart = Cart(id=new_id, items=[], price=0.0)

    # Вставляем в Mongo
    await collection.insert_one(new_cart.model_dump())

    return new_cart


async def get_cart_by_id(mongo, cart_id: int) -> Cart | None:
    """
    Получение корзины по id.
    Возвращает Pydantic-модель Cart или None, если корзина не найдена.
    """
    collection = mongo.mongo["carts"]

    doc = await collection.find_one({"id": cart_id})
    if not doc:
        return None

    return Cart(**doc)


async def get_carts(
    mongo,
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> tuple[list[Cart] | None, int]:
    """
    Получение списка корзин с фильтрацией и пагинацией.
    Возвращает (list[Cart], status_code)
    """
    # Валидация входных параметров
    if (
        offset < 0
        or limit <= 0
        or (min_price is not None and min_price < 0)
        or (max_price is not None and max_price < 0)
        or (min_quantity is not None and min_quantity < 0)
        or (max_quantity is not None and max_quantity < 0)
    ):
        return None, 422

    collection = mongo.mongo["carts"]

    # Формируем фильтр для MongoDB
    filter_query = {}

    if min_price is not None or max_price is not None:
        filter_query["price"] = {}
        if min_price is not None:
            filter_query["price"]["$gte"] = min_price
        if max_price is not None:
            filter_query["price"]["$lte"] = max_price

    if min_quantity is not None or max_quantity is not None:
        filter_query["items"] = {}
        if min_quantity is not None:
            filter_query["items"]["$size"] = {"$gte": min_quantity}  # $size не поддерживает диапазоны
        # MongoDB не поддерживает напрямую max для $size, фильтруем после
        # поэтому будем фильтровать вручную ниже

    # Получаем документы с сортировкой по id и пагинацией
    cursor = collection.find(filter_query).sort("id", 1).skip(offset).limit(limit)
    carts = [Cart(**doc) async for doc in cursor]

    # Дополнительная фильтрация по max_quantity, так как $size не поддерживает диапазон
    if max_quantity is not None:
        carts = [cart for cart in carts if len(cart.items) <= max_quantity]

    return carts, 200


async def add_item_to_cart(mongo, cart_id: int, item_id: int) -> tuple[Cart | None, int]:
    """
    Добавляет товар в корзину. Если товар уже есть — увеличивает quantity.
    Возвращает (Cart, status_code) или (None, 404), если корзина/товар не найдены.
    """
    from app.crud.item import get_item_by_id

    carts_collection = mongo.mongo["carts"]

    # Получаем корзину
    cart_doc = await carts_collection.find_one({"id": cart_id})
    if not cart_doc:
        return None, 404

    # Получаем товар
    item_to_add = await get_item_by_id(mongo, item_id)
    if not item_to_add:
        return None, 404

    # Флаг, был ли товар добавлен
    is_item_added = False
    cart_items = cart_doc.get("items", [])
    for idx, cart_item in enumerate(cart_items):
        if cart_item["id"] == item_id:
            cart_items[idx]["quantity"] += 1
            cart_doc["price"] += item_to_add.price
            is_item_added = True
            break

    # Если товара нет в корзине, добавляем новый
    if not is_item_added:
        new_cart_item = ItemCart(
            id=item_to_add.id, name=item_to_add.name, quantity=1, available=not item_to_add.deleted
        )
        cart_items.append(new_cart_item.model_dump())
        cart_doc["price"] += item_to_add.price

    # Обновляем корзину в MongoDB
    cart_doc["items"] = cart_items
    updated_cart_doc = await carts_collection.find_one_and_update(
        {"id": cart_id},
        {"$set": {"items": cart_items, "price": cart_doc["price"]}},
        return_document=ReturnDocument.AFTER,
    )

    return Cart(**updated_cart_doc), 200