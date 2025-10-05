from fastapi import FastAPI, Response, Query, HTTPException
from typing import Optional
import uvicorn
import json
import os
from http import HTTPStatus

app = FastAPI(title="Shop API")

carts_file = "carts.json"
items_file = "items.json"

def load_json(file_path):
    if not os.path.exists(file_path):
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({}, f)
    with open(file_path, 'r', encoding='utf-8') as f:
        carts = json.load(f)
    return carts

def save_json(json_file, file_path):
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(json_file, f, indent=4)


### CART
@app.post("/cart")
def create_cart():

    carts = load_json(carts_file)
    if carts:
        cart_id = max(carts.keys())
    else:
        cart_id = 1
    carts[cart_id] = {'id': cart_id, 'items': [], 'price': 0.0 }

    save_json(carts, carts_file)

    response = Response(
        content=json.dumps(carts[cart_id]),
        status_code=HTTPStatus.CREATED,
        media_type="application/json",
        headers={}
    )
    response.headers["Location"] = f"/cart/{cart_id}"
    return response

@app.get("/cart/{cart_id}")
def get_cart(cart_id: int):
    carts = load_json(carts_file)
    return carts[str(cart_id)]

@app.get("/cart")
def get_carts(
        offset: int = Query(0, ge=0, description="Смещение по списку"),
        limit: int = Query(10, gt=0, description="Ограничение на количество"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
        min_quantity: Optional[int] = Query(None, ge=0, description="Минимальное количество товаров"),
        max_quantity: Optional[int] = Query(None, ge=0, description="Максимальное количество товаров")
):
    carts = load_json(carts_file)
    cart_list = list(carts.values())

    filtered_carts = []

    for cart in cart_list:
        # Фильтр по цене
        price_ok = True
        if min_price is not None and cart['price'] < min_price:
            price_ok = False
        if max_price is not None and cart['price'] > max_price:
            price_ok = False
        if not price_ok:
            continue

        filtered_carts.append(cart)

    # Теперь применяем фильтры min_quantity/max_quantity ко всему результату
    # Эти фильтры работают на уровне всего набора данных

    if min_quantity is not None or max_quantity is not None:
        # Вычисляем общее количество товаров во всех отфильтрованных корзинах
        total_quantity_all_carts = sum(
            item['quantity']
            for cart in filtered_carts
            for item in cart['items']
        )

        # Проверяем условия для всего набора
        if min_quantity is not None and total_quantity_all_carts < min_quantity:
            # Если общее количество меньше min_quantity, возвращаем пустой список
            filtered_carts = []
        elif max_quantity is not None and total_quantity_all_carts > max_quantity:
            # Если общее количество больше max_quantity, возвращаем пустой список
            filtered_carts = []

    # Сортируем по ID
    filtered_carts.sort(key=lambda x: x['id'])

    # Пагинация
    start_idx = offset
    end_idx = offset + limit
    result = filtered_carts[start_idx:end_idx]

    return result

@app.post("/cart/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int):
    carts = load_json(carts_file)
    items = load_json(items_file)
    item = items[str(item_id)]
    cart = carts[str(cart_id)]

    # Проверяем, есть ли товар в корзине
    item_found = False
    for cart_item in cart['items']:
        if cart_item['id'] == item_id:
            # Если товар уже есть, увеличиваем quantity на 1
            cart_item['quantity'] += 1
            item_found = True
            break

    # Если товара нет в корзине, добавляем его
    if not item_found:
        cart['items'].append(item)

    # Пересчитываем общую стоимость корзины
    total_price = 0.0
    for cart_item in cart['items']:
        total_price += cart_item['price'] * cart_item['quantity']
    cart['price'] = total_price

    save_json(carts, carts_file)
    return carts[str(cart_id)]

### ITEM

@app.post("/item")
def create_item(item: dict):
    items = load_json(items_file)
    if items:
        item_id = str(max(items.keys()))
    else:
        item_id = str(1)
    item['id'] = int(item_id)
    item['quantity'] = 1
    items[item_id] = item


    save_json(items, items_file)

    response = Response(
        content=json.dumps(items[item_id]),
        status_code=HTTPStatus.CREATED,
        media_type="application/json",
        headers={}
    )
    return response


@app.get("/item/{item_id}")
def get_item(item_id: int):
    items = load_json(items_file)

    if str(item_id) not in items:
        raise HTTPException(status_code=404, detail="Item not found")

    item = items[str(item_id)]

    # Для удаленных товаров возвращаем 404
    if item.get('deleted', False):
        raise HTTPException(status_code=404, detail="Item not found")

    return item


@app.get("/item")
def get_items(
        offset: int = Query(0, ge=0, description="Смещение по списку"),
        limit: int = Query(10, gt=0, description="Ограничение на количество"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
        show_deleted: bool = Query(False, description="Показывать удаленные товары")
):
    items = load_json(items_file)
    item_list = list(items.values())

    filtered_items = []

    for item in item_list:
        # Фильтр по статусу удаления
        if not show_deleted and item.get('deleted', False):
            continue

        # Фильтр по цене
        price_ok = True
        if min_price is not None and item['price'] < min_price:
            price_ok = False
        if max_price is not None and item['price'] > max_price:
            price_ok = False
        if not price_ok:
            continue

        filtered_items.append(item)

    # Сортируем по ID (или можно по другому полю)
    filtered_items.sort(key=lambda x: x['id'])

    # Пагинация
    start_idx = offset
    end_idx = offset + limit
    result = filtered_items[start_idx:end_idx]

    return result


@app.put("/item/{item_id}")
def update_item(item_id: int, item_data: dict):
    items = load_json(items_file)

    # Проверяем существование товара
    if str(item_id) not in items:
        raise HTTPException(status_code=404, detail="Item not found")

    item = items[str(item_id)]

    # Проверяем, что товар не удален
    if item.get('deleted', False):
        raise HTTPException(status_code=404, detail="Item not found")

    # Проверяем обязательные поля
    if 'name' not in item_data or 'price' not in item_data:
        raise HTTPException(
            status_code=422,
            detail="Name and price are required for PUT"
        )

    # Полная замена товара (сохраняем только id и переданные поля)
    updated_item = {
        'id': item_id,
        'name': item_data['name'],
        'price': item_data['price'],
        'quantity': 1
    }

    items[str(item_id)] = updated_item
    save_json(items, items_file)

    return updated_item


@app.patch("/item/{item_id}")
def patch_item(item_id: int, item_data: dict):
    items = load_json(items_file)

    if str(item_id) not in items:
        raise HTTPException(status_code=404, detail="Item not found")

    item = items[str(item_id)]

    # Для удаленных товаров возвращаем 304
    if item.get('deleted', False):
        raise HTTPException(status_code=304, detail="Item is deleted")

    # Проверяем на лишние поля
    allowed_fields = {'name', 'price'}
    extra_fields = set(item_data.keys()) - allowed_fields
    if extra_fields:
        raise HTTPException(
            status_code=422,
            detail=f"Extra fields not allowed: {extra_fields}"
        )

    # Запрещаем менять deleted
    if 'deleted' in item_data:
        raise HTTPException(status_code=422, detail="Cannot change deleted status")

    # Если тело пустое - возвращаем текущий товар без изменений
    if not item_data:
        return item

    # Частичное обновление
    if 'name' in item_data:
        item['name'] = item_data['name']

    if 'price' in item_data:
        if item_data['price'] < 0:
            raise HTTPException(status_code=422, detail="Price cannot be negative")
        item['price'] = item_data['price']

    save_json(items, items_file)
    return item


@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    items = load_json(items_file)

    if str(item_id) not in items:
        return HTTPStatus.NOT_FOUND

    item = items[str(item_id)]

    # Если уже удален - все равно успех
    if not item.get('deleted', False):
        item['deleted'] = True
        save_json(items, items_file)

    # Возвращаем просто сообщение, а не весь item
    return HTTPStatus.OK


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)