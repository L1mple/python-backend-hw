from fastapi import FastAPI, Response, HTTPException, status
from pydantic import BaseModel, conint, confloat

from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from fastapi import Depends

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

DB_HOST = "postgres"
DB_PORT = "5432"
DB_NAME = "hw4_db"
DB_USER = "postgres"
DB_PASSWORD = "password"
DATABASE_URL = (
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
engine = create_engine(
    DATABASE_URL,
    echo=False
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class ItemOrm(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

class CartOrm(Base):
    __tablename__ = "carts"
    id = Column(Integer, primary_key=True, index=True)
    price = Column(Float, default=0.0)
    items = relationship("CartItemOrm", back_populates="cart")

class CartItemOrm(Base):
    __tablename__ = "cart_items"
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    name = Column(String)
    price = Column(Float)
    quantity = Column(Integer, default=1)
    cart = relationship("CartOrm", back_populates="items")

Base.metadata.create_all(bind=engine)
app = FastAPI(title="Shop API")

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
async def create_cart(response: Response, db: Session = Depends(get_db)):
    new_cart = CartOrm()
    db.add(new_cart)
    db.commit()
    db.refresh(new_cart)
    response.headers["Location"] = f"/cart/{new_cart.id}"
    return {"id": new_cart.id}


# GET /cart/{id} - получение корзины по id
@app.get("/cart/{cart_id}", status_code=status.HTTP_200_OK)
async def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = db.query(CartOrm).filter(CartOrm.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404)
    return {
        "id": cart.id,
        "price": cart.price,
        "items": [
            {
                "id": i.item_id,
                "name": i.name,
                "price": i.price,
                "quantity": i.quantity,
            }
            for i in cart.items
        ]
    }


# GET /cart - получение списка корзин с query-параметрами
#    offset - неотрицательное целое число, смещение по списку (опционально, по-умолчанию 0)
#    limit - положительное целое число, ограничение на количество (опционально, по-умолчанию 10)
#    min_price - число с плавающей запятой, минимальная цена включительно (опционально, если нет, не учитывает в фильтре)
#    max_price - число с плавающей запятой, максимальная цена включительно (опционально, если нет, не учитывает в фильтре)
#    min_quantity - неотрицательное целое число, минимальное общее число товаров включительно (опционально, если нет, не учитывается в фильтре)
#    max_quantity - неотрицательное целое число, максимальное общее число товаров включительно (опционально, если нет, не учитывается в фильтре)
@app.get("/cart", status_code=status.HTTP_200_OK)
async def get_cart_list(
        offset: uint = 0, limit: posint = 10,
        min_price: ufloat = None, max_price: ufloat = None,
        min_quantity: uint = None, max_quantity: uint = None,
        db: Session = Depends(get_db)
):
    query = db.query(CartOrm)

    if min_price is not None:
        query = query.filter(CartOrm.price >= min_price)
    if max_price is not None:
        query = query.filter(CartOrm.price <= max_price)

    carts = query.offset(offset).limit(limit).all()

    result = []
    for cart in carts:
        total_quantity = sum(i.quantity for i in cart.items)
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        result.append({
            "id": cart.id,
            "price": cart.price,
            "items": [
                {
                    "id": i.item_id,
                    "name": i.name,
                    "price": i.price,
                    "quantity": i.quantity
                }
                for i in cart.items
            ],
        })

    return result


# POST /cart/{cart_id}/add/{item_id} - добавление в корзину с cart_id предмета с item_id,
# если товар уже есть, то увеличивается его количество
@app.post("/cart/{cart_id}/add/{item_id}", status_code=status.HTTP_200_OK)
async def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.query(CartOrm).filter(CartOrm.id == cart_id).first()
    item = db.query(ItemOrm).filter(ItemOrm.id == item_id, ItemOrm.deleted == False).first()
    if not cart or not item:
        raise HTTPException(status_code=404)
    cart_item = db.query(CartItemOrm).filter_by(cart_id=cart.id, item_id=item.id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItemOrm(
            cart_id=cart.id,
            item_id=item.id,
            name=item.name,
            price=item.price,
            quantity=1
        )
        db.add(cart_item)
    cart.price += item.price
    db.commit()
    db.refresh(cart)


"""
item
"""

# POST /item - добавление нового товара
@app.post("/item", status_code=status.HTTP_201_CREATED)
async def create_item(item: Item, db: Session = Depends(get_db)):
    db_item = ItemOrm(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


# GET /item/{id} - получение товара по id
@app.get("/item/{item_id}", status_code=status.HTTP_200_OK)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
    if not db_item or db_item.deleted:
        raise HTTPException(status_code=404)
    return db_item


# GET /item - получение списка товаров с query-параметрами
#    offset - неотрицательное целое число, смещение по списку (опционально, по-умолчанию 0)
#    limit - положительное целое число, ограничение на количество (опционально, по-умолчанию 10)
#    min_price - число с плавающей запятой, минимальная цена (опционально, если нет, не учитывает в фильтре)
#    max_price - число с плавающей запятой, максимальная цена (опционально, если нет, не учитывает в фильтре)
#    show_deleted - булевая переменная, показывать ли удаленные товары (по умолчанию False)
@app.get("/item", status_code=status.HTTP_200_OK)
async def get_item_list(
        offset: uint = 0, limit: posint = 10,
        min_price: ufloat = None, max_price: ufloat = None,
        show_deleted: bool = False,
        db: Session = Depends(get_db)
):
    query = db.query(ItemOrm)
    if not show_deleted:
        query = query.filter(ItemOrm.deleted == False)
    if min_price is not None:
        query = query.filter(ItemOrm.price >= min_price)
    if max_price is not None:
        query = query.filter(ItemOrm.price <= max_price)
    return query.offset(offset).limit(limit).all()


# PUT /item/{id} - замена товара по id (создание запрещено, только замена существующего)
@app.put("/item/{item_id}", status_code=status.HTTP_200_OK)
async def put_item(item_id: int, item: Item, db: Session = Depends(get_db)):
    db_item = db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    db_item.name = item.name
    db_item.price = item.price
    db.commit()
    db.refresh(db_item)
    return db_item


# PATCH /item/{id} - частичное обновление товара по id (разрешено менять все поля, кроме deleted)
@app.patch("/item/{item_id}", status_code=status.HTTP_200_OK)
async def patch_item(item_id: int, item: ModifiedItem, db: Session = Depends(get_db)):
    db_item = db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if db_item.deleted:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)

    if item.name is not None and db_item.name != item.name:
        db_item.name = item.name
    if item.price is not None and db_item.price != item.price:
        db_item.price = item.price
    db.commit()
    db.refresh(db_item)
    return db_item


# DELETE /item/{id} - удаление товара по id (товар помечается как удаленный)
@app.delete("/item/{item_id}", status_code=status.HTTP_200_OK)
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404)
    db_item.deleted = True
    db.commit()