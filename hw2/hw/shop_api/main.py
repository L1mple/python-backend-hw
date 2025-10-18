from fastapi import FastAPI, Response, Query, HTTPException
from typing import Optional, List
import uvicorn
import json
import os
from http import HTTPStatus

from prometheus_fastapi_instrumentator import Instrumentator
import asyncpg
import redis.asyncio as redis
from datetime import datetime
from pydantic import BaseModel
from fastapi.encoders import jsonable_encoder
from decimal import Decimal

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


# Модели данных
class CartItem(BaseModel):
    product_id: int
    quantity: int
    price: float


class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float
    created_at: Optional[datetime] = None


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False
    created_at: Optional[datetime] = None


# Подключение к БД
async def get_db_connection():
    return await asyncpg.connect(
        database=os.getenv('POSTGRES_DB', 'shop'),
        user=os.getenv('POSTGRES_USER', 'user'),
        password=os.getenv('POSTGRES_PASSWORD', 'password'),
        host=os.getenv('POSTGRES_HOST', 'postgres'),
        port=os.getenv('POSTGRES_PORT', '5432')
    )


# Redis подключение
async def get_redis_connection():
    return redis.Redis(
        host=os.getenv('REDIS_HOST', 'redis'),
        port=os.getenv('REDIS_PORT', 6379),
        decode_responses=True
    )


# Вспомогательные функции
async def get_cart_from_db(cart_id: int) -> Optional[dict]:
    """Получить корзину из БД"""
    db_conn = await get_db_connection()
    try:
        # Получаем основную информацию о корзине
        cart = await db_conn.fetchrow(
            "SELECT id, total_price as price, created_at FROM carts WHERE id = $1",
            cart_id
        )

        if not cart:
            return None

        # Получаем товары в корзине
        items = await db_conn.fetch(
            """SELECT product_id, quantity, price 
               FROM cart_items WHERE cart_id = $1""",
            cart_id
        )

        # Конвертируем Decimal в float сразу
        cart_data = {
            'id': cart['id'],
            'items': [{
                'id': item['product_id'],
                'quantity': item['quantity'],
                'price': float(item['price'])  # Конвертируем здесь
            } for item in items],
            'price': float(cart['price']),  # Конвертируем здесь
            'created_at': cart['created_at'].isoformat() if cart['created_at'] else None
        }

        return cart_data
    finally:
        await db_conn.close()

async def get_cart_with_cache(cart_id: int) -> Optional[dict]:
    """Получить корзину с кешированием"""
    redis_conn = await get_redis_connection()

    try:
        # Пробуем получить из кеша
        cached_cart = await redis_conn.get(f"cart:{cart_id}")
        if cached_cart:
            cart_data = json.loads(cached_cart)
            # Конвертируем Decimal при получении из кеша
            if cart_data and 'price' in cart_data:
                cart_data['price'] = float(cart_data['price'])
                for item in cart_data.get('items', []):
                    if 'price' in item:
                        item['price'] = float(item['price'])
            return cart_data

        # Если нет в кеше, получаем из БД
        cart_data = await get_cart_from_db(cart_id)

        if cart_data:
            # Конвертируем Decimal перед сохранением в кеш
            cart_data_for_cache = cart_data.copy()
            cart_data_for_cache['price'] = float(cart_data_for_cache['price'])
            for item in cart_data_for_cache.get('items', []):
                item['price'] = float(item['price'])

            # Сохраняем в кеш на 5 минут
            await redis_conn.setex(f"cart:{cart_id}", 300, json.dumps(cart_data_for_cache, cls=DecimalEncoder))

        return cart_data
    finally:
        await redis_conn.aclose()


async def invalidate_cart_cache(cart_id: int):
    """Инвалидировать кеш корзины"""
    redis_conn = await get_redis_connection()
    try:
        await redis_conn.delete(f"cart:{cart_id}")
    finally:
        await redis_conn.aclose()


async def get_item_from_db(item_id: int) -> Optional[dict]:
    """Получить товар из БД"""
    db_conn = await get_db_connection()
    try:
        item = await db_conn.fetchrow(
            "SELECT id, name, price, deleted FROM products WHERE id = $1",  # Исключаем created_at
            item_id
        )

        if not item:
            return None

        return {
            'id': item['id'],
            'name': item['name'],
            'price': float(item['price']),
            'deleted': item['deleted']
        }
    finally:
        await db_conn.close()


### CART ENDPOINTS

@app.post("/cart")
async def create_cart():
    db_conn = await get_db_connection()

    try:
        # Создаем новую корзину
        cart_id = await db_conn.fetchval(
            "INSERT INTO carts (total_price) VALUES (0.00) RETURNING id"
        )

        # Создаем ответ
        cart_data = {
            'id': cart_id,
            'items': [],
            'price': 0.0,
            'created_at': datetime.now().isoformat()
        }

        response = Response(
            content=json.dumps(cart_data),
            status_code=HTTPStatus.CREATED,
            media_type="application/json",
            headers={}
        )
        response.headers["Location"] = f"/cart/{cart_id}"
        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating cart: {str(e)}")
    finally:
        await db_conn.close()


@app.get("/cart/{cart_id}")
async def get_cart(cart_id: int):
    cart_data = await get_cart_with_cache(cart_id)

    if not cart_data:
        raise HTTPException(status_code=404, detail="Cart not found")

    return cart_data


@app.get("/cart")
async def get_carts(
        offset: int = Query(0, ge=0, description="Смещение по списку"),
        limit: int = Query(10, gt=0, description="Ограничение на количество"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
        min_quantity: Optional[int] = Query(None, ge=0, description="Минимальное количество товаров"),
        max_quantity: Optional[int] = Query(None, ge=0, description="Максимальное количество товаров")
):
    db_conn = await get_db_connection()

    try:
        # Базовый запрос
        query = """
            SELECT c.id, c.total_price as price, c.created_at,
                   COALESCE(SUM(ci.quantity), 0) as total_quantity
            FROM carts c
            LEFT JOIN cart_items ci ON c.id = ci.cart_id
        """

        where_conditions = []
        params = []
        param_count = 0

        # Фильтры по цене
        if min_price is not None:
            param_count += 1
            where_conditions.append(f"c.total_price >= ${param_count}")
            params.append(min_price)

        if max_price is not None:
            param_count += 1
            where_conditions.append(f"c.total_price <= ${param_count}")
            params.append(max_price)

        # Добавляем условия WHERE если есть фильтры
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)

        # Группировка для подсчета общего количества товаров
        query += " GROUP BY c.id, c.total_price, c.created_at"

        # Получаем все корзины
        carts = await db_conn.fetch(query, *params)

        # Преобразуем в нужный формат и фильтруем по количеству товаров
        result_carts = []
        for cart in carts:
            # Получаем товары для каждой корзины
            items = await db_conn.fetch(
                "SELECT product_id, quantity, price FROM cart_items WHERE cart_id = $1",
                cart['id']
            )

            cart_data = {
                'id': cart['id'],
                'items': [dict(item) for item in items],
                'price': float(cart['price']),
                'created_at': cart['created_at'].isoformat() if cart['created_at'] else None
            }

            result_carts.append(cart_data)

        # Фильтрация по общему количеству товаров (min_quantity/max_quantity)
        if min_quantity is not None or max_quantity is not None:
            filtered_carts = []

            for cart_data in result_carts:
                total_items_quantity = sum(item['quantity'] for item in cart_data['items'])

                quantity_ok = True
                if min_quantity is not None and total_items_quantity < min_quantity:
                    quantity_ok = False
                if max_quantity is not None and total_items_quantity > max_quantity:
                    quantity_ok = False

                if quantity_ok:
                    filtered_carts.append(cart_data)

            result_carts = filtered_carts

        # Сортируем по ID
        result_carts.sort(key=lambda x: x['id'])

        # Пагинация
        start_idx = offset
        end_idx = offset + limit
        paginated_result = result_carts[start_idx:end_idx]

        return paginated_result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting carts: {str(e)}")
    finally:
        await db_conn.close()


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int):
    db_conn = await get_db_connection()

    try:
        # Проверяем существование корзины
        cart_exists = await db_conn.fetchval(
            "SELECT 1 FROM carts WHERE id = $1", cart_id
        )
        if not cart_exists:
            raise HTTPException(status_code=404, detail="Cart not found")

        # Проверяем существование товара
        item = await db_conn.fetchrow(
            "SELECT id, name, price FROM products WHERE id = $1 AND NOT deleted", item_id
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        async with db_conn.transaction():
            # Проверяем, есть ли товар уже в корзине
            existing_item = await db_conn.fetchrow(
                "SELECT quantity, price FROM cart_items WHERE cart_id = $1 AND product_id = $2",
                cart_id, item_id
            )

            if existing_item:
                # Обновляем количество
                await db_conn.execute(
                    "UPDATE cart_items SET quantity = quantity + 1 WHERE cart_id = $1 AND product_id = $2",
                    cart_id, item_id
                )
                price_to_add = float(existing_item['price'])
            else:
                # Добавляем новый товар
                await db_conn.execute(
                    """INSERT INTO cart_items (cart_id, product_id, quantity, price)
                       VALUES ($1, $2, 1, $3)""",
                    cart_id, item_id, float(item['price'])
                )
                price_to_add = float(item['price'])

            # Обновляем общую стоимость корзины
            await db_conn.execute(
                "UPDATE carts SET total_price = total_price + $1, updated_at = CURRENT_TIMESTAMP WHERE id = $2",
                price_to_add, cart_id
            )

        # Инвалидируем кеш корзины
        await invalidate_cart_cache(cart_id)

        # Возвращаем обновленную корзину с конвертацией Decimal
        cart_data = await get_cart_with_cache(cart_id)
        if cart_data:
            # Конвертируем все Decimal значения в float
            cart_data['price'] = float(cart_data['price'])
            for item in cart_data['items']:
                item['price'] = float(item['price'])

        return jsonable_encoder(cart_data)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error adding to cart: {str(e)}")
    finally:
        await db_conn.close()

### ITEM ENDPOINTS


@app.get("/item/{item_id}")
async def get_item(item_id: int):
    item_data = await get_item_from_db(item_id)

    if not item_data:
        raise HTTPException(status_code=404, detail="Item not found")

    # Для удаленных товаров возвращаем 404
    if item_data.get('deleted', False):
        raise HTTPException(status_code=404, detail="Item not found")

    # Добавляем quantity для обратной совместимости
    item_data['quantity'] = 1

    return item_data


@app.get("/item")
async def get_items(
        offset: int = Query(0, ge=0, description="Смещение по списку"),
        limit: int = Query(10, gt=0, description="Ограничение на количество"),
        min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена"),
        max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена"),
        show_deleted: bool = Query(False, description="Показывать удаленные товары")
):
    db_conn = await get_db_connection()

    try:
        # Базовый запрос
        query = "SELECT id, name, price, deleted, created_at FROM products"
        where_conditions = []
        params = []
        param_count = 0

        # Фильтр по статусу удаления
        if not show_deleted:
            where_conditions.append("NOT deleted")

        # Фильтры по цене
        if min_price is not None:
            param_count += 1
            where_conditions.append(f"price >= ${param_count}")
            params.append(float(min_price))

        if max_price is not None:
            param_count += 1
            where_conditions.append(f"price <= ${param_count}")
            params.append(float(max_price))

        # Добавляем условия WHERE если есть фильтры
        if where_conditions:
            query += " WHERE " + " AND ".join(where_conditions)

        # Сортировка
        query += " ORDER BY id"

        # Теперь правильно добавляем пагинацию
        # Сначала считаем общее количество параметров
        total_params = len(params)

        # Добавляем LIMIT и OFFSET с правильными номерами параметров
        query += f" LIMIT ${total_params + 1} OFFSET ${total_params + 2}"
        params.extend([limit, offset])

        items = await db_conn.fetch(query, *params)

        result = []
        for item in items:
            item_data = {
                'id': item['id'],
                'name': item['name'],
                'price': float(item['price']),
                'quantity': 1,  # Для обратной совместимости
                'deleted': item['deleted'],
                'created_at': item['created_at'].isoformat() if item['created_at'] else None
            }
            result.append(item_data)

        return jsonable_encoder(result)

    except Exception as e:
        print(f"Error in get_items: {e}")  # Для отладки
        raise HTTPException(status_code=500, detail=f"Error getting items: {str(e)}")
    finally:
        await db_conn.close()


@app.post("/item")
async def create_item(item_data: dict):
    db_conn = await get_db_connection()

    try:
        # Проверяем обязательные поля
        if 'name' not in item_data or 'price' not in item_data:
            raise HTTPException(
                status_code=422,
                detail="Name and price are required"
            )

        # Создаем товар
        if float(item_data['price']) < 0:
            raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY)
        item_id = await db_conn.fetchval(
            """INSERT INTO products (name, price, deleted) 
               VALUES ($1, $2, false) RETURNING id""",
            item_data['name'], float(item_data['price'])
        )

        # Получаем созданный товар (без created_at для совместимости)
        item = await db_conn.fetchrow(
            "SELECT id, name, price, deleted FROM products WHERE id = $1",
            item_id
        )

        item_response = {
            'id': item['id'],
            'name': item['name'],
            'price': float(item['price']),
            'quantity': 1,  # Для обратной совместимости
            'deleted': item['deleted']
            # Исключаем created_at для совместимости с тестами
        }

        response = Response(
            content=json.dumps(jsonable_encoder(item_response)),
            status_code=HTTPStatus.CREATED,
            media_type="application/json",
            headers={}
        )
        return response

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating item: {str(e)}")
    finally:
        await db_conn.close()


@app.put("/item/{item_id}")
async def update_item(item_id: int, item_data: dict):
    db_conn = await get_db_connection()

    try:
        # Проверяем существование товара
        existing_item = await db_conn.fetchrow(
            "SELECT id, deleted FROM products WHERE id = $1", item_id
        )
        if not existing_item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Проверяем, что товар не удален
        if existing_item['deleted']:
            raise HTTPException(status_code=404, detail="Item not found")

        # Проверяем обязательные поля
        if 'name' not in item_data or 'price' not in item_data:
            raise HTTPException(
                status_code=422,
                detail="Name and price are required for PUT"
            )
        if float(item_data['price']) < 0:
            raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY)
        # Обновляем товар
        await db_conn.execute(
            "UPDATE products SET name = $1, price = $2 WHERE id = $3",
            item_data['name'], float(item_data['price']), item_id
        )

        # Получаем обновленный товар (без created_at)
        updated_item = await db_conn.fetchrow(
            "SELECT id, name, price, deleted FROM products WHERE id = $1",
            item_id
        )

        response = {
            'id': updated_item['id'],
            'name': updated_item['name'],
            'price': float(updated_item['price']),
            'quantity': 1,
            'deleted': updated_item['deleted']
            # Исключаем created_at
        }

        return jsonable_encoder(response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating item: {str(e)}")
    finally:
        await db_conn.close()


@app.patch("/item/{item_id}")
async def patch_item(item_id: int, item_data: dict):
    db_conn = await get_db_connection()

    try:
        # Проверяем существование товара
        existing_item = await db_conn.fetchrow(
            "SELECT id, name, price, deleted FROM products WHERE id = $1", item_id
        )
        if not existing_item:
            raise HTTPException(status_code=404, detail="Item not found")

        # Для удаленных товаров возвращаем 304
        if existing_item['deleted']:
            raise HTTPException(status_code=304, detail="Item is deleted")

        # Проверяем на лишние поля
        allowed_fields = {'name', 'price'}
        extra_fields = set(item_data.keys()) - allowed_fields
        if extra_fields:
            raise HTTPException(
                status_code=422,
                detail=f"Extra fields not allowed: {extra_fields}"
            )
        if float(item_data['price']) < 0:
            raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY)
        # Если тело пустое - возвращаем текущий товар без изменений
        if not item_data:
            response = {
                'id': existing_item['id'],
                'name': existing_item['name'],
                'price': float(existing_item['price']),
                'quantity': 1,
                'deleted': existing_item['deleted']
                # Исключаем created_at
            }
            return jsonable_encoder(response)

        # Подготавливаем данные для обновления
        update_fields = []
        update_params = []
        param_count = 0

        if 'name' in item_data:
            param_count += 1
            update_fields.append(f"name = ${param_count}")
            update_params.append(item_data['name'])

        if 'price' in item_data:
            if item_data['price'] < 0:
                raise HTTPException(status_code=422, detail="Price cannot be negative")
            param_count += 1
            update_fields.append(f"price = ${param_count}")
            update_params.append(float(item_data['price']))

        # Выполняем обновление
        if update_fields:
            param_count += 1
            update_query = f"UPDATE products SET {', '.join(update_fields)} WHERE id = ${param_count}"
            update_params.append(item_id)
            await db_conn.execute(update_query, *update_params)

        # Получаем обновленный товар (без created_at)
        updated_item = await db_conn.fetchrow(
            "SELECT id, name, price, deleted FROM products WHERE id = $1",
            item_id
        )

        response = {
            'id': updated_item['id'],
            'name': updated_item['name'],
            'price': float(updated_item['price']),
            'quantity': 1,
            'deleted': updated_item['deleted']
            # Исключаем created_at
        }

        return jsonable_encoder(response)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error patching item: {str(e)}")
    finally:
        await db_conn.close()


@app.delete("/item/{item_id}")
async def delete_item(item_id: int):
    db_conn = await get_db_connection()

    try:
        # Проверяем существование товара
        existing_item = await db_conn.fetchrow(
            "SELECT id, deleted FROM products WHERE id = $1", item_id
        )
        if not existing_item:
            return Response(status_code=HTTPStatus.NOT_FOUND)

        # Если уже удален - все равно успех
        if not existing_item['deleted']:
            await db_conn.execute(
                "UPDATE products SET deleted = true WHERE id = $1",
                item_id
            )

        # Возвращаем просто статус OK
        return Response(status_code=HTTPStatus.OK)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting item: {str(e)}")
    finally:
        await db_conn.close()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
