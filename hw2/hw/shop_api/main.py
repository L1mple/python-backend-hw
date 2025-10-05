from fastapi import FastAPI, Response, HTTPException, status
from pydantic import BaseModel, conint, confloat

app = FastAPI(title="Shop API")
cart_id_counter = 0
item_id_counter = 0

carts = {}
items = {}

posint = conint(gt=0)
uint = conint(ge=0)
ufloat = confloat(ge=0)

class ModifiedItem(BaseModel):
    name: str | None = None
    price: float | None = None
    model_config = {
        "extra": "forbid"
    }

class Item(BaseModel):
    id: uint = 0
    name: str
    price: float
    deleted: bool = False

class CartItem(BaseModel):
    id: uint = 0
    name: str
    price: float
    quantity: int = 0
    deleted: bool = False

class Cart(BaseModel):
    id: int
    price: float = 0.0
    items: list[CartItem] = []


"""
cart
"""

# POST cart - создание, работает как RPC, не принимает тело, возвращает идентификатор
@app.post("/cart", status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response):
    global cart_id_counter
    cart_id_counter += 1
    new_cart = Cart(
        id=cart_id_counter
    )
    carts[new_cart.id] = new_cart
    response.headers["Location"] = f"/cart/{new_cart.id}"
    return {"id": new_cart.id}


# GET /cart/{id} - получение корзины по id
@app.get("/cart/{cart_id}", status_code=status.HTTP_200_OK)
async def get_cart(cart_id: int):
    return carts[cart_id]


# GET /cart - получение списка корзин с query-параметрами
#    offset - неотрицательное целое число, смещение по списку (опционально, по-умолчанию 0)
#    limit - положительное целое число, ограничение на количество (опционально, по-умолчанию 10)
#    min_price - число с плавающей запятой, минимальная цена включительно (опционально, если нет, не учитывает в фильтре)
#    max_price - число с плавающей запятой, максимальная цена включительно (опционально, если нет, не учитывает в фильтре)
#    min_quantity - неотрицательное целое число, минимальное общее число товаров включительно (опционально, если нет, не учитывается в фильтре)
#    max_quantity - неотрицательное целое число, максимальное общее число товаров включительно (опционально, если нет, не учитывается в фильтре)
@app.get("/cart", status_code=status.HTTP_200_OK)
async def get_cart_list(offset: uint = 0, limit: posint = 10,
                        min_price: ufloat = None, max_price: ufloat = None,
                        min_quantity: uint = None, max_quantity: uint = None):
    filtered_carts = []
    for cart in list(carts.values())[offset:]:
        if len(filtered_carts) == limit:
            break

        min_price_ok = cart.price >= min_price if min_price else True
        max_price_ok = cart.price <= max_price if max_price else True
        min_quantity_ok = sum(item.quantity for item in cart.items) >= min_quantity if not min_quantity is None else True
        max_quantity_ok = sum(item.quantity for item in cart.items) <= max_quantity if not max_quantity is None else True

        if min_price_ok and max_price_ok and min_quantity_ok and max_quantity_ok:
            filtered_carts.append(cart)
    return filtered_carts


# POST /cart/{cart_id}/add/{item_id} - добавление в корзину с cart_id предмета с item_id,
# если товар уже есть, то увеличивается его количество
@app.post("/cart/{cart_id}/add/{item_id}", status_code=status.HTTP_200_OK)
async def add_to_cart(cart_id: int, item_id: int):
    cart = carts[cart_id]
    item = items[item_id]

    item_exists = False
    for i in range(len(cart.items)):
        if cart.items[i].id == item_id:
            cart.items[i].quantity += 1
            item_exists = True
            break

    if not item_exists:
        new_item = CartItem(
            **item.model_dump(),
            quantity=1
        )
        cart.items.append(new_item)

    cart.price += item.price


"""
item
"""

# POST /item - добавление нового товара
@app.post("/item", status_code=status.HTTP_201_CREATED)
async def create_item(item: Item):
    global item_id_counter
    item_id_counter += 1
    new_item = Item(id=item_id_counter, name=item.name, price=item.price)
    items[new_item.id] = new_item
    return new_item

# GET /item/{id} - получение товара по id
@app.get("/item/{item_id}", status_code=status.HTTP_200_OK)
async def get_item(item_id: int):
    if items[item_id].deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND
        )
    return items[item_id]
    

# GET /item - получение списка товаров с query-параметрами
#    offset - неотрицательное целое число, смещение по списку (опционально, по-умолчанию 0)
#    limit - положительное целое число, ограничение на количество (опционально, по-умолчанию 10)
#    min_price - число с плавающей запятой, минимальная цена (опционально, если нет, не учитывает в фильтре)
#    max_price - число с плавающей запятой, максимальная цена (опционально, если нет, не учитывает в фильтре)
#    show_deleted - булевая переменная, показывать ли удаленные товары (по умолчанию False)
@app.get("/item", status_code=status.HTTP_200_OK)
async def get_item_list(offset: uint = 0, limit: posint = 10,
                        min_price: ufloat = None, max_price: ufloat = None,
                        show_deleted: bool = False):
    filtered_items = []
    for item in list(items.values())[offset:]:
        if len(filtered_items) == limit:
            break

        min_price_ok = item.price >= min_price if min_price else True
        max_price_ok = item.price <= max_price if max_price else True
        show_deleted_ok = (not item.deleted) or show_deleted

        if min_price_ok and max_price_ok and show_deleted_ok:
            filtered_items.append(item)

    return filtered_items

# PUT /item/{id} - замена товара по id (создание запрещено, только замена существующего)
@app.put("/item/{item_id}", status_code=status.HTTP_200_OK)
async def put_item(item_id: int, new_item: Item):
    new_item.id = item_id
    items[item_id] = new_item
    return new_item

# PATCH /item/{id} - частичное обновление товара по id (разрешено менять все поля, кроме deleted)
@app.patch("/item/{item_id}", status_code=status.HTTP_200_OK)
async def patch_item(item_id: int, new_item: ModifiedItem):
    item = items[item_id]
    if item.deleted:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)
    if new_item.name and item.name != new_item.name:
        items[item_id].name = new_item.name
    if new_item.price and item.price != new_item.price:
        items[item_id].price = new_item.price
    return items[item_id]

# DELETE /item/{id} - удаление товара по id (товар помечается как удаленный)
@app.delete("/item/{item_id}", status_code=status.HTTP_200_OK)
async def delete_item(item_id: int):
    items[item_id].deleted = True
