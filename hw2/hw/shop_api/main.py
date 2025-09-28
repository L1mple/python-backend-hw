from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Response, status

from .models import Cart, CartItem, Item, ItemBase, ItemUpdate

app = FastAPI(title='Shop API')

item_id_seq = 1
items_db: dict[int, Item] = {}  # хранение в памяти
cart_id_seq = 1
carts_db: dict[int, Cart] = {}


@app.post('/item', response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemBase):
    """POST /item - добавление нового товара"""
    global item_id_seq
    item_data = Item(
        id=item_id_seq,
        name=item.name,
        price=item.price,
        deleted=False,
    )
    items_db[item_id_seq] = item_data
    item_id_seq += 1
    return item_data


@app.get('/item/{item_id}', response_model=Item)
def get_item(item_id: int):
    """GET /item/{id} - получение товара по id"""
    item = items_db.get(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail='Item not found')
    return item


@app.get('/item', response_model=List[Item])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
):
    """
    GET /item - получение списка товаров с query-параметрами
    Args:
        offset: неотрицательное целое число, смещение по списку (опционально, по-умолчанию 0)
        limit: положительное целое число, ограничение на количество (опционально, по-умолчанию 10)
        min_price: число с плавающей запятой, минимальная цена (опционально, если нет, не учитывает в фильтре)
        max_price: число с плавающей запятой, максимальная цена (опционально, если нет, не учитывает в фильтре)
        show_deleted: булевая переменная, показывать ли удаленные товары (по умолчанию False)
    """
    items = list(items_db.values())
    if min_price is not None:
        items = [item for item in items if item.price >= min_price]
    if max_price is not None:
        items = [item for item in items if item.price <= max_price]
    if not show_deleted:
        items = [item for item in items if not item.deleted]
    return items[offset : offset + limit]


@app.put('/item/{item_id}', response_model=Item)
def replace_item(item_id: int, item: ItemBase):
    """PUT /item/{id} - замена товара по id (создание запрещено, только замена существующего)"""
    if item_id not in items_db or items_db[item_id].deleted:
        raise HTTPException(status_code=404, detail='Item not found')
    items_db[item_id].name = item.name
    items_db[item_id].price = item.price
    return items_db[item_id]


@app.patch('/item/{item_id}', response_model=Item)
def update_item(item_id: int, item: ItemUpdate, response: Response):
    """PATCH /item/{id} - частичное обновление товара по id (разрешено менять все поля, кроме deleted)"""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail='Item not found')

    if items_db[item_id].deleted:
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return items_db[item_id]

    if item.name:
        items_db[item_id].name = item.name
    if item.price:
        items_db[item_id].price = item.price

    return items_db[item_id]


@app.delete('/item/{item_id}')
def delete_item(item_id: int):
    """DELETE /item/{id} - удаление товара по id (товар помечается как удаленный)"""
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail='Item not found')
    items_db[item_id].deleted = True
    return {'item_id': item_id}


@app.post('/cart', response_model=Cart, status_code=status.HTTP_201_CREATED)
def create_cart(response: Response):
    """POST cart - создание, работает как RPC, не принимает тело, возвращает идентификатор"""
    global cart_id_seq

    cart_data = Cart(
        id=cart_id_seq,
        items=[],
        price=0.0,
    )
    carts_db[cart_id_seq] = cart_data
    cart_id_seq += 1

    response.headers['Location'] = f'/cart/{cart_data.id}'
    return cart_data


@app.get('/cart/{cart_id}', response_model=Cart)
def get_cart(cart_id: int):
    """GET /cart/{id} - получение корзины по id"""
    cart = carts_db.get(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail='Cart not found')
    return cart


def count_total_quantity(cart: Cart) -> int:
    return sum(item.quantity for item in cart.items)


@app.get('/cart', response_model=List[Cart])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    """
    GET /cart - получение списка корзин с query-параметрами
    Args:
        offset: неотрицательное целое число, смещение по списку (опционально, по-умолчанию 0)
        limit: положительное целое число, ограничение на количество (опционально, по-умолчанию 10)
        min_price: число с плавающей запятой, минимальная цена включительно (опционально, если нет, не учитывает в фильтре)
        max_price: число с плавающей запятой, максимальная цена включительно (опционально, если нет, не учитывает в фильтре)
        min_quantity: неотрицательное целое число, минимальное общее число товаров включительно (опционально, если нет, не учитывается в фильтре)
        max_quantity: неотрицательное целое число, максимальное общее число товаров включительно (опционально, если нет, не учитывается в фильтре)
    """
    carts = list(carts_db.values())

    if min_price is not None:
        carts = [cart for cart in carts if cart.price >= min_price]
    if max_price is not None:
        carts = [cart for cart in carts if cart.price <= max_price]

    if min_quantity is not None:
        carts = [cart for cart in carts if count_total_quantity(cart) >= min_quantity]
    if max_quantity is not None:
        carts = [cart for cart in carts if count_total_quantity(cart) <= max_quantity]

    return carts[offset : offset + limit]


@app.post('/cart/{cart_id}/add/{item_id}', response_model=Cart)
def add_item_to_cart(cart_id: int, item_id: int):
    """
    POST /cart/{cart_id}/add/{item_id} - добавление в корзину с cart_id
    предмета с item_id, если товар уже есть, то увеличивается его количество
    """
    cart = carts_db.get(cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail='Cart not found')

    item = items_db.get(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail='Item not found')

    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            break
    else:
        cart.items.append(
            CartItem(
                id=item.id,
                name=item.name,
                quantity=1,
                available=not item.deleted,
            )
        )

    cart.price = sum(item.quantity * items_db[item.id].price for item in cart.items)
    return cart
