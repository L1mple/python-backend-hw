from fastapi import FastAPI, HTTPException, status, Response
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid

app = FastAPI(title="Shop API")

# Хранение данных в памяти
items_db: Dict[int, Dict] = {}
carts_db: Dict[int, Dict] = {}

# Счетчики для генерации ID
item_counter = 0
cart_counter = 0

# Модели данных
class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: List[CartItem]
    price: float

# Вспомогательные функции
def get_next_item_id():
    global item_counter
    item_counter += 1
    return item_counter

def get_next_cart_id():
    global cart_counter
    cart_counter += 1
    return cart_counter

def calculate_cart_price(cart):
    """ИСПРАВЛЕННАЯ ФУНКЦИЯ: не использует поле 'available'"""
    total = 0.0
    for item in cart["items"]:
        item_data = items_db.get(item["id"])
        # Проверяем доступность товара через items_db
        if item_data and not item_data["deleted"]:
            total += item_data["price"] * item["quantity"]
    return total

# API для корзин
@app.post("/cart", status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response):
    cart_id = get_next_cart_id()
    carts_db[cart_id] = {
        "id": cart_id,
        "items": []
    }
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}

@app.get("/cart/{cart_id}", response_model=CartResponse)
async def get_cart(cart_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart = carts_db[cart_id]
    response_items = []
    
    for item in cart["items"]:
        item_data = items_db.get(item["id"])
        available = item_data is not None and not item_data["deleted"]
        response_items.append({
            "id": item["id"],
            "name": item["name"],
            "quantity": item["quantity"],
            "available": available
        })
    
    price = calculate_cart_price(cart)
    
    return {
        "id": cart_id,
        "items": response_items,
        "price": price
    }

@app.get("/cart")
async def get_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None
):
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
    
    carts_list = list(carts_db.values())
    result = []
    
    for cart in carts_list:
        response_items = []
        for item in cart["items"]:
            item_data = items_db.get(item["id"])
            available = item_data is not None and not item_data["deleted"]
            response_items.append({
                "id": item["id"],
                "name": item["name"],
                "quantity": item["quantity"],
                "available": available
            })
        
        price = calculate_cart_price(cart)
        total_quantity = sum(item["quantity"] for item in response_items)
        
        # Фильтрация по цене
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        
        # Фильтрация по количеству товаров
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        
        result.append({
            "id": cart["id"],
            "items": response_items,
            "price": price
        })
    
    return result[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item_data = items_db[item_id]
    cart = carts_db[cart_id]
    
    # Проверяем, есть ли товар уже в корзине
    for cart_item in cart["items"]:
        if cart_item["id"] == item_id:
            cart_item["quantity"] += 1
            return {"message": "Item quantity increased"}
    
    # Добавляем новый товар
    cart["items"].append({
        "id": item_id,
        "name": item_data["name"],
        "quantity": 1
    })
    
    return {"message": "Item added to cart"}

# API для товаров
@app.post("/item", status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate):
    item_id = get_next_item_id()
    items_db[item_id] = {
        "id": item_id,
        "name": item.name,
        "price": item.price,
        "deleted": False
    }
    return items_db[item_id]

@app.get("/item/{item_id}")
async def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item = items_db[item_id]
    if item["deleted"]:
        raise HTTPException(status_code=404, detail="Item not found")
    
    return item

@app.get("/item")
async def get_items(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False
):
    if offset < 0:
        raise HTTPException(status_code=422, detail="Offset must be non-negative")
    if limit <= 0:
        raise HTTPException(status_code=422, detail="Limit must be positive")
    if min_price is not None and min_price < 0:
        raise HTTPException(status_code=422, detail="Min price must be non-negative")
    if max_price is not None and max_price < 0:
        raise HTTPException(status_code=422, detail="Max price must be non-negative")
    
    items_list = list(items_db.values())
    
    # Фильтрация по удаленным товарам
    if not show_deleted:
        items_list = [item for item in items_list if not item["deleted"]]
    
    # Фильтрация по цене
    if min_price is not None:
        items_list = [item for item in items_list if item["price"] >= min_price]
    if max_price is not None:
        items_list = [item for item in items_list if item["price"] <= max_price]
    
    return items_list[offset:offset + limit]

@app.put("/item/{item_id}")
async def update_item(item_id: int, item: ItemCreate):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    existing_item = items_db[item_id]
    if existing_item["deleted"]:
        raise HTTPException(status_code=304)
    
    items_db[item_id].update({
        "name": item.name,
        "price": item.price
    })
    
    return items_db[item_id]

@app.patch("/item/{item_id}")
async def partial_update_item(item_id: int, item_update: Dict[str, Any]):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    existing_item = items_db[item_id]
    if existing_item["deleted"]:
        raise HTTPException(status_code=304)
    
    # Проверяем, что не пытаемся изменить поле deleted
    if "deleted" in item_update:
        raise HTTPException(status_code=422, detail="Cannot modify deleted field")
    
    # Проверяем, что все поля валидны
    allowed_fields = {"name", "price"}
    for field in item_update:
        if field not in allowed_fields:
            raise HTTPException(status_code=422, detail=f"Field {field} is not allowed")
    
    # Обновляем только переданные поля
    for field, value in item_update.items():
        items_db[item_id][field] = value
    
    return items_db[item_id]

@app.delete("/item/{item_id}")
async def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    
    items_db[item_id]["deleted"] = True
    return {"message": "Item deleted"}