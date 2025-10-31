import os
from http import HTTPStatus
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, confloat
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy import (Boolean, Column, Float, ForeignKey, Integer, String,
                        create_engine, select)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/shopdb")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Модели SQLAlchemy
class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    price = Column(Float)
    deleted = Column(Boolean, default=False)

    cart_items = relationship("CartItemDB", back_populates="item")


class CartDB(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    items = relationship("CartItemDB", back_populates="cart", cascade="all, delete-orphan")


class CartItemDB(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantity = Column(Integer, default=1)

    cart = relationship("CartDB", back_populates="items")
    item = relationship("ItemDB", back_populates="cart_items")


# Настройка FastAPI
app = FastAPI(title="Shop API")

@app.on_event("startup")
def on_startup():
    # Создаем таблицы в БД при старте приложения
    Base.metadata.create_all(bind=engine)

Instrumentator().instrument(app).expose(app)


# Pydantic схемы
class BaseItem(BaseModel):
    name: str = Field(..., min_length=1)
    price: confloat(gt=0.0)


class Item(BaseItem):
    id: int
    deleted: bool = False

    class Config:
        orm_mode = True


class ItemUpdate(BaseItem):
    pass


class PartialItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[confloat(gt=0.0)] = None


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    class Config:
        orm_mode = True


class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float


class CartCreated(BaseModel):
    id: int

# Зависимость для получения сессии БД
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Вспомогательные функции
def get_item_or_404(db: Session, item_id: int, include_deleted: bool = False) -> ItemDB:
    item = db.get(ItemDB, item_id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Item with id {item_id} not found")
    if item.deleted and not include_deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Item with id {item_id} not found")
    return item


def get_cart_or_404(db: Session, cart_id: int) -> CartDB:
    cart = db.get(CartDB, cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Cart with id {cart_id} not found")
    return cart


def calculate_cart_details(cart_db: CartDB) -> (List[CartItem], float):
    items_list = []
    total_price = 0.0
    for cart_item in cart_db.items:
        item_db = cart_item.item
        is_available = not item_db.deleted
        items_list.append(
            CartItem(
                id=item_db.id,
                name=item_db.name,
                quantity=cart_item.quantity,
                available=is_available,
            )
        )
        if is_available:
            total_price += item_db.price * cart_item.quantity
    return items_list, total_price


# Эндпоинты
@app.post("/item", response_model=Item, status_code=HTTPStatus.CREATED)
async def create_item(item: BaseItem, db: Session = Depends(get_db)):
    new_item = ItemDB(name=item.name, price=item.price)
    db.add(new_item)
    db.commit()
    db.refresh(new_item)
    return new_item


@app.get("/item/{item_id}", response_model=Item)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    return get_item_or_404(db, item_id)


@app.get("/item", response_model=List[Item])
async def get_item_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = False,
    db: Session = Depends(get_db),
):
    query = select(ItemDB)
    if not show_deleted:
        query = query.where(ItemDB.deleted == False)
    if min_price is not None:
        query = query.where(ItemDB.price >= min_price)
    if max_price is not None:
        query = query.where(ItemDB.price <= max_price)
    
    items = db.scalars(query.offset(offset).limit(limit)).all()
    return items


@app.put("/item/{item_id}", response_model=Item)
async def update_item(item_id: int, item_update: ItemUpdate, db: Session = Depends(get_db)):
    db_item = get_item_or_404(db, item_id)
    db_item.name = item_update.name
    db_item.price = item_update.price
    db.commit()
    db.refresh(db_item)
    return db_item


@app.patch("/item/{item_id}", response_model=Item)
async def partially_update_item(
    item_id: int, item_update: PartialItemUpdate, response: Response, db: Session = Depends(get_db)
):
    db_item = get_item_or_404(db, item_id, include_deleted=True)
    if db_item.deleted:
        response.status_code = HTTPStatus.NOT_MODIFIED
        return db_item
        
    update_data = item_update.dict(exclude_unset=True)
    if not update_data:
        return db_item
        
    for key, value in update_data.items():
        setattr(db_item, key, value)
        
    db.commit()
    db.refresh(db_item)
    return db_item


@app.delete("/item/{item_id}", response_model=Item)
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = get_item_or_404(db, item_id, include_deleted=True)
    db_item.deleted = True
    db.commit()
    db.refresh(db_item)
    return db_item


@app.post("/cart", response_model=CartCreated, status_code=HTTPStatus.CREATED)
async def create_cart(response: Response, db: Session = Depends(get_db)):
    new_cart = CartDB()
    db.add(new_cart)
    db.commit()
    db.refresh(new_cart)
    response.headers["Location"] = f"/cart/{new_cart.id}"
    return {"id": new_cart.id}


@app.get("/cart/{cart_id}", response_model=Cart)
async def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart_db = get_cart_or_404(db, cart_id)
    items_list, total_price = calculate_cart_details(cart_db)
    return Cart(id=cart_db.id, items=items_list, price=total_price)


@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
async def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart_db = get_cart_or_404(db, cart_id)
    _ = get_item_or_404(db, item_id)

    # Ищем, есть ли уже такой товар в корзине
    cart_item = db.execute(
        select(CartItemDB).where(CartItemDB.cart_id == cart_id, CartItemDB.item_id == item_id)
    ).scalar_one_or_none()

    if cart_item:
        cart_item.quantity += 1
    else:
        new_cart_item = CartItemDB(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(new_cart_item)
    
    db.commit()
    db.refresh(cart_db)

    items_list, total_price = calculate_cart_details(cart_db)
    return Cart(id=cart_db.id, items=items_list, price=total_price)