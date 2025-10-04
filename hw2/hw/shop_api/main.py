from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from http import HTTPStatus
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import json

from . import db

# Создаем менеджер БД
db_manager = db.DatabaseManager()

def get_db() -> Session:
    db = db_manager.get_session()
    try:
        yield db  # Возвращаем сессию
    finally:
        db.close()  # Закрываем после использования

app = FastAPI(title="Shop API")

class OptionalBaseItem(BaseModel):
    model_config = ConfigDict(extra='forbid') # ЗАПРЕТИТ СУЩЕСТВОВАНИЕ ДРУГИХ АТРИБУТОВ В JSON
    name: str | None = Field(None, min_length=1)
    price: float | None = Field(None, gt=0)

class BaseItem(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    deleted: bool = False

class Item(BaseItem):
    id: int = Field(ge=0)

    # "id": 321, // идентификатор товара
    # "name": "Молоко \"Буреночка\" 1л.", // наименование товара
    # "price": 159.99, // цена товара
    # "deleted": false // удален ли товар, по умолчанию false


@app.post("/item")
def create_new_item(new_item: BaseItem, db_session: Session = Depends(get_db)):
    db_item = db.Item(name=new_item.name, price=new_item.price, deleted=new_item.deleted)
    # 2. Добавляем в сессию
    db_session.add(db_item)
    # 3. Сохраняем в БД
    db_session.commit()
    # 4. Обновляем объект (получаем сгенерированный ID)
    db_session.refresh(db_item)
    
    return {"id": db_item.id, "name": db_item.name, "price": db_item.price}

@app.get("/item/{id}")
def read_item_by_id(id: int, db_session: Session = Depends(get_db)):
    item = db_session.query(db.Item).filter(db.Item.id == id).first()
    if not item:
        return HTTPException(HTTPStatus.NOT_FOUND, detail=f"Item with id {id} not found")
    
    return {
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "deleted": item.deleted
    }

@app.get("/item")
def get_items_by_filtering(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
    db_session: Session = Depends(get_db)
    ):
    # 1. Начинаем с базового запроса
    query = db_session.query(db.Item)
    
    # 2. Применяем фильтры условно
    if not show_deleted:
        query = query.filter(db.Item.deleted == False)
    
    if min_price is not None:
        query = query.filter(db.Item.price >= min_price)
    
    if max_price is not None:
        query = query.filter(db.Item.price <= max_price)
    
    # 3. Применяем пагинацию
    items = query.offset(offset).limit(limit).all()

    list_items = [{"id": item.id, "name": item.name, "price": item.price, "deleted": item.deleted} for item in items]
    
    return list_items

@app.put("/item/{id}")
def put_data_by_id(id: int, fixed_item: BaseItem, db_session: Session = Depends(get_db)):
    # Находим запись по id
    item = db_session.query(db.Item).filter(db.Item.id == id).first()
    
    if not item:
        raise HTTPException(HTTPStatus.NOT_FOUND, detail=f"Item with id {id} not found")
    
    # Обновляем поля
    item.name = fixed_item.name
    item.price = fixed_item.price
    item.deleted = fixed_item.deleted
    
    # Сохраняем изменения
    db_session.commit()
    
    return {
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "deleted": item.deleted
    }

@app.patch("/item/{id}")
def patch_item_by_id(id: int, fixed_item: OptionalBaseItem, db_session: Session = Depends(get_db)):
    if fixed_item.name is None and fixed_item.price is None:
        return HTTPException(HTTPStatus.BAD_REQUEST)
    
    # Находим запись по id
    item = db_session.query(db.Item).filter(db.Item.id == id).first()
    
    if not item:
        raise HTTPException(HTTPStatus.NOT_FOUND, detail=f"Item with id {id} not found")
    
    # Обновляем поля
    if fixed_item.name:
        item.name = fixed_item.name
    if fixed_item.price:
        item.price = fixed_item.price
    
    # Сохраняем изменения
    db_session.commit()
    
    return {
        "id": item.id,
        "name": item.name,
        "price": item.price,
        "deleted": item.deleted
    }

@app.delete("/item/{id}")
def delete_item_by_id(id: int, db_session: Session = Depends(get_db)):
     # Находим запись по id
    item = db_session.query(db.Item).filter(db.Item.id == id).first()
    
    if not item:
        raise HTTPException(HTTPStatus.NOT_FOUND, detail=f"Item with id {id} not found")
    
    db_session.delete(item)
    db_session.commit()

    return HTTPStatus.OK

# -------------------------------------------------------------------------------------------

@app.post("/cart")
def create_new_cart(db_session: Session = Depends(get_db)):
    db_item = db.Cart(items=[], price=0)
    # 2. Добавляем в сессию
    db_session.add(db_item)
    # 3. Сохраняем в БД
    db_session.commit()
    # 4. Обновляем объект (получаем сгенерированный ID)
    db_session.refresh(db_item)
    
    return {"id": db_item.id}

@app.get("/cart/{id}")
def get_cart_by_id(id: int, db_session: Session = Depends(get_db)):
    item = db_session.query(db.Cart).filter(db.Cart.id == id).first()
    if not item:
        return HTTPException(HTTPStatus.NOT_FOUND, detail=f"Cart with id {id} not found")
    
    return item

@app.get("/cart")
def get_carts_by_filtering(
    offset: Optional[int] = 0,
    limit: Optional[int] = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
    db_session: Session = Depends(get_db)
    ):
    # Базовый запрос
    query = db_session.query(db.Cart)
    
    # Фильтрация
    if min_quantity is not None:
        query = query.filter(func.json_array_length(db.Cart.items) >= min_quantity)

    if max_quantity is not None:
        query = query.filter(func.json_array_length(db.Cart.items) <= max_quantity)
    
    if min_price is not None:
        query = query.filter(db.Cart.price >= min_price)
    
    if max_price is not None:
        query = query.filter(db.Cart.price <= max_price)
    
    # 3. Применяем пагинацию
    carts = query.offset(offset).limit(limit).all()

    return carts

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db_session: Session = Depends(get_db)):
    # первым делом надо проверить что объекты с такими id вообще есть в базах
    item = db_session.query(db.Item).filter(db.Item.id == item_id).first()
    if not item:
        raise HTTPException(HTTPStatus.NOT_FOUND, detail=f"Item with id {item_id} not found")

    cart = db_session.query(db.Cart).filter(db.Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(HTTPStatus.NOT_FOUND, detail=f"Cart with id {cart_id} not found")
    
    # ПРАВИЛЬНЫЙ способ для JSON колонки:
    # 1. Получаем текущий список (или создаем пустой)
    items_list = list(cart.items) if cart.items else []
    print(items_list)
    
    # 2. Проверяем, есть ли товар уже в корзине
    item_found = False
    for i, cart_item in enumerate(items_list):
        if cart_item["id"] == item_id:
            # Товар уже есть - увеличиваем количество
            items_list[i]["quantity"] += 1
            print(f"\n\n\nUPDATE - {items_list[i]["quantity"]}\n\n\n")
            item_found = True
            break
    
    # 3. Если товара нет - добавляем новый
    if not item_found:
        print(f"\n\n\nNOT FOUND\n\n\n")
        items_list.append({
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "quantity": 1,
            "deleted": item.deleted
        })
    
    # 4. КРИТИЧНО: Переприсваиваем список (SQLAlchemy отследит изменение)
    cart.items = items_list

    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(cart, "items")
    
    # 5. Пересчитываем цену
    total_price = 0.0
    for cart_item in items_list:
        # Получаем актуальную цену товара из БД
        db_item = db_session.query(db.Item).filter(db.Item.id == cart_item["id"]).first()
        if db_item:
            total_price += db_item.price * cart_item["quantity"]
    
    cart.price = total_price
    
    # 6. Сохраняем изменения
    db_session.commit()
    db_session.refresh(cart)

    # 7. Возвращаем корзину (не статус!)
    return {
        "id": cart.id,
        "items": cart.items,
        "price": cart.price
    }