from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field

app = FastAPI(title="Shop API")


# Модели данных
class Item(BaseModel):
    id: int
    name: str
    price: float = Field(gt=0)
    deleted: bool = False


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int = Field(ge=1)
    available: bool


class Cart(BaseModel):
    id: int
    items: List[CartItem] = []
    price: float = Field(ge=0)


# Хранилище данных в памяти
items_db: Dict[int, Item] = {}
carts_db: Dict[int, Cart] = {}
next_item_id = 1
next_cart_id = 1


# Вспомогательные функции
def get_next_item_id() -> int:
    global next_item_id
    next_item_id += 1
    return next_item_id - 1


def get_next_cart_id() -> int:
    global next_cart_id
    next_cart_id += 1
    return next_cart_id - 1


def calculate_cart_price(cart: Cart) -> float:
    total = 0.0
    for item in cart.items:
        if item.available:
            item_obj = items_db.get(item.id)
            if item_obj and not item_obj.deleted:
                total += item_obj.price * item.quantity
    return total


# Эндпоинты для корзин
@app.post("/cart", status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response):
    cart_id = get_next_cart_id()
    cart = Cart(id=cart_id, items=[], price=0.0)
    carts_db[cart_id] = cart
    response.headers["location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@app.get("/cart/{cart_id}")
async def get_cart(cart_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=404, detail="Cart not found")

    cart = carts_db[cart_id]
    # Пересчитываем цену на случай изменений в товарах
    cart.price = calculate_cart_price(cart)
    return cart


@app.get("/cart")
async def get_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
):
    # Валидация параметров
    if offset < 0:
        raise HTTPException(status_code=422, detail="Offset must be non-negative")
    if limit <= 0:
        raise HTTPException(status_code=422, detail="Limit must be positive")
    if min_price is not None and min_price < 0:
        raise HTTPException(status_code=422, detail="Min price must be non-negative")
    if max_price is not None and max_price < 0:
        raise HTTPException(status_code=422, detail="Max price must be non-negative")
    if min_quantity is not None and min_quantity < 0:
        raise HTTPException(status_code=422, detail="Min quantity must be non-negative")
    if max_quantity is not None and max_quantity < 0:
        raise HTTPException(status_code=422, detail="Max quantity must be non-negative")

    carts = list(carts_db.values())

    # Применяем фильтры
    filtered_carts = []
    for cart in carts:
        # Пересчитываем цену для каждого запроса
        cart.price = calculate_cart_price(cart)

        # Фильтр по цене
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue

        filtered_carts.append(cart)

    # Применяем пагинацию
    paginated_carts = filtered_carts[offset : offset + limit]

    # ВАЖНО: фильтр по quantity применяется к суммарному количеству
    # товаров во ВСЕХ возвращаемых корзинах (после пагинации)
    if min_quantity is not None or max_quantity is not None:
        total_quantity = sum(
            item.quantity for cart in paginated_carts for item in cart.items
        )

        if min_quantity is not None and total_quantity < min_quantity:
            return []
        if max_quantity is not None and total_quantity > max_quantity:
            return []

    return paginated_carts


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    item = items_db[item_id]
    if item.deleted:
        raise HTTPException(status_code=400, detail="Item is deleted")

    cart = carts_db[cart_id]

    # Проверяем, есть ли товар уже в корзине
    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            cart.price = calculate_cart_price(cart)
            return {"message": "Item quantity increased"}

    # Добавляем новый товар
    cart_item = CartItem(
        id=item_id, name=item.name, quantity=1, available=not item.deleted
    )
    cart.items.append(cart_item)
    cart.price = calculate_cart_price(cart)

    return {"message": "Item added to cart"}


# Эндпоинты для товаров
class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)


class ItemPut(BaseModel):
    """Модель для PUT - все поля обязательны"""

    name: str
    price: float = Field(gt=0)


class ItemPatch(BaseModel):
    """Модель для PATCH - все поля опциональны, extra поля запрещены"""

    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    price: Optional[float] = Field(gt=0, default=None)


@app.post("/item", status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate):
    item_id = get_next_item_id()
    new_item = Item(id=item_id, name=item.name, price=item.price)
    items_db[item_id] = new_item
    return new_item


@app.get("/item/{item_id}")
async def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    item = items_db[item_id]
    # Возвращаем 404 для удаленных товаров
    if item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")

    return item


@app.get("/item")
async def get_items(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
):
    # Валидация параметров
    if offset < 0:
        raise HTTPException(status_code=422, detail="Offset must be non-negative")
    if limit <= 0:
        raise HTTPException(status_code=422, detail="Limit must be positive")
    if min_price is not None and min_price < 0:
        raise HTTPException(status_code=422, detail="Min price must be non-negative")
    if max_price is not None and max_price < 0:
        raise HTTPException(status_code=422, detail="Max price must be non-negative")

    items = list(items_db.values())

    # Фильтрация
    filtered_items = []
    for item in items:
        if not show_deleted and item.deleted:
            continue

        if min_price is not None and item.price < min_price:
            continue
        if max_price is not None and item.price > max_price:
            continue

        filtered_items.append(item)

    # Пагинация
    result = filtered_items[offset : offset + limit]
    return result


@app.put("/item/{item_id}")
async def update_item(item_id: int, item_update: ItemPut):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    existing_item = items_db[item_id]
    if existing_item.deleted:
        raise HTTPException(status_code=400, detail="Cannot update deleted item")

    # Обновляем поля
    existing_item.name = item_update.name
    existing_item.price = item_update.price

    return existing_item


@app.patch("/item/{item_id}")
async def partial_update_item(item_id: int, item_update: ItemPatch):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    existing_item = items_db[item_id]

    # Для удаленных товаров возвращаем 304 NOT_MODIFIED
    if existing_item.deleted:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)

    # Обновляем только переданные поля
    update_data = item_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(existing_item, field, value)

    return existing_item


@app.delete("/item/{item_id}")
async def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    items_db[item_id].deleted = True
    return {"message": "Item deleted successfully"}
