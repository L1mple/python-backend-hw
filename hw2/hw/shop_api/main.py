from typing import List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.orm import Session

from . import database, schemas
from .database import get_db

app = FastAPI(title='Shop API')
Instrumentator().instrument(app).expose(app)


@app.post('/item', response_model=schemas.Item, status_code=status.HTTP_201_CREATED)
def create_item(item: schemas.ItemBase, db: Session = Depends(get_db)):
    """POST /item - добавление нового товара"""
    item = database.Item(name=item.name, price=item.price)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get('/item/{item_id}', response_model=schemas.Item)
def get_item(item_id: int, db: Session = Depends(get_db)):
    """GET /item/{id} - получение товара по id"""
    item = db.query(database.Item).filter_by(id=item_id, deleted=False).first()
    if not item:
        raise HTTPException(status_code=404, detail='Item not found')
    return item


@app.get('/item', response_model=List[schemas.Item])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
    db: Session = Depends(get_db),
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
    query = db.query(database.Item)
    if not show_deleted:
        query = query.filter_by(deleted=False)
    if min_price is not None:
        query = query.filter(database.Item.price >= min_price)
    if max_price is not None:
        query = query.filter(database.Item.price <= max_price)
    items = query.offset(offset).limit(limit).all()
    return items


@app.put('/item/{item_id}', response_model=schemas.Item)
def replace_item(item_id: int, item: schemas.ItemBase, db: Session = Depends(get_db)):
    """PUT /item/{id} - замена товара по id (создание запрещено, только замена существующего)"""
    db_item = db.query(database.Item).filter_by(id=item_id, deleted=False).first()
    if not db_item:
        raise HTTPException(status_code=404, detail='Item not found')

    db_item.name = item.name
    db_item.price = item.price

    db.commit()
    db.refresh(db_item)
    return db_item


@app.patch('/item/{item_id}', response_model=schemas.Item)
def update_item(
    item_id: int,
    item: schemas.ItemUpdate,
    response: Response,
    db: Session = Depends(get_db),
):
    """PATCH /item/{id} - частичное обновление товара по id (разрешено менять все поля, кроме deleted)"""
    item = db.query(database.Item).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Item not found')

    if item.deleted:
        response.status_code = status.HTTP_304_NOT_MODIFIED
        return item

    if item.name is not None:
        item.name = item.name
    if item.price is not None:
        item.price = item.price

    db.commit()
    db.refresh(item)
    return item


@app.delete('/item/{item_id}')
def delete_item(item_id: int, db: Session = Depends(get_db)):
    """DELETE /item/{id} - удаление товара по id (товар помечается как удаленный)"""
    item = db.query(database.Item).filter_by(id=item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail='Item not found')
    item.deleted = True
    db.commit()
    return {'item_id': item_id}


@app.post('/cart', response_model=schemas.Cart, status_code=status.HTTP_201_CREATED)
def create_cart(response: Response, db: Session = Depends(get_db)):
    """POST cart - создание, работает как RPC, не принимает тело, возвращает идентификатор"""
    cart = database.Cart(price=0.0)
    db.add(cart)
    db.commit()
    db.refresh(cart)
    response.headers['Location'] = f'/cart/{cart.id}'
    return schemas.Cart(id=cart.id, items=[], price=cart.price)


@app.get('/cart/{cart_id}', response_model=schemas.Cart)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    """GET /cart/{id} - получение корзины по id"""
    cart = db.query(database.Cart).filter_by(id=cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail='Cart not found')

    cart_items = []
    for cart_item in cart.items:
        cart_items.append(
            schemas.CartItem(
                id=cart_item.item.id,
                name=cart_item.item.name,
                quantity=cart_item.quantity,
                available=not cart_item.item.deleted,
            )
        )

    return schemas.Cart(id=cart.id, items=cart_items, price=cart.price)


@app.get('/cart', response_model=List[schemas.Cart])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
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
    query = db.query(database.Cart)
    if min_price is not None:
        query = query.filter(database.Cart.price >= min_price)
    if max_price is not None:
        query = query.filter(database.Cart.price <= max_price)
    carts = query.offset(offset).limit(limit).all()

    result = []
    for cart in carts:
        total_quantity = sum(cart_item.quantity for cart_item in cart.items)
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        items = [
            schemas.CartItem(
                id=cart_item.item.id,
                name=cart_item.item.name,
                quantity=cart_item.quantity,
                available=not cart_item.item.deleted,
            )
            for cart_item in cart.items
        ]
        result.append(schemas.Cart(id=cart.id, items=items, price=cart.price))
    return result


@app.post('/cart/{cart_id}/add/{item_id}', response_model=schemas.Cart)
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    """
    POST /cart/{cart_id}/add/{item_id} - добавление в корзину с cart_id
    предмета с item_id, если товар уже есть, то увеличивается его количество
    """
    cart = db.get(database.Cart, cart_id)
    if not cart:
        raise HTTPException(status_code=404, detail='Cart not found')

    item = db.get(database.Item, item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail='Item not found')

    cart_item = (
        db.query(database.CartItem).filter_by(cart_id=cart.id, item_id=item.id).first()
    )

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = database.CartItem(cart_id=cart.id, item_id=item.id, quantity=1)
        db.add(cart_item)

    db.commit()

    total = (
        db.query(database.CartItem)
        .join(database.Item)
        .with_entities(database.CartItem.quantity * database.Item.price)
        .filter(database.CartItem.cart_id == cart.id)
        .all()
    )
    cart.price = sum(v[0] for v in total)
    db.commit()
    db.refresh(cart)

    items = []
    for ci in cart.items:
        items.append(
            schemas.CartItem(
                id=ci.item.id,
                name=ci.item.name,
                quantity=ci.quantity,
                available=not ci.item.deleted,
            )
        )

    return schemas.Cart(id=cart.id, price=cart.price, items=items)
