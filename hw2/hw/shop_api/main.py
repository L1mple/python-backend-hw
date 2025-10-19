from http import HTTPStatus
from typing import Annotated
import os

from fastapi import FastAPI, HTTPException, Query, Response, Depends
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Numeric
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.sql import func

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://shop_user:shop_password@localhost:5432/shop_db")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)


# ==================== Database Models ====================


class ItemOrm(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    deleted = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CartOrm(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class CartItemOrm(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ==================== Pydantic Models ====================


class ItemCreateRequest(BaseModel):
    name: str
    price: float = Field(gt=0)


class ItemPatchRequest(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, gt=0)

    @field_validator("price", "name")
    @classmethod
    def check_no_deleted(cls, v, info):
        return v

    model_config = {"extra": "forbid"}


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    items: list[CartItem]
    price: float


class CartResponse(BaseModel):
    id: int


# ==================== Storage ====================


class Storage:
    def __init__(self, db: Session):
        self.db = db

    def create_item(self, name: str, price: float) -> Item:
        item_orm = ItemOrm(name=name, price=price, deleted=False)
        self.db.add(item_orm)
        self.db.commit()
        self.db.refresh(item_orm)
        return Item(
            id=item_orm.id,
            name=item_orm.name,
            price=float(item_orm.price),
            deleted=item_orm.deleted
        )

    def get_item(self, item_id: int) -> Item | None:
        item_orm = self.db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
        if not item_orm:
            return None
        return Item(
            id=item_orm.id,
            name=item_orm.name,
            price=float(item_orm.price),
            deleted=item_orm.deleted
        )

    def get_items(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        show_deleted: bool = False,
    ) -> list[Item]:
        query = self.db.query(ItemOrm)

        # Apply filters
        if not show_deleted:
            query = query.filter(ItemOrm.deleted == False)

        if min_price is not None:
            query = query.filter(ItemOrm.price >= min_price)

        if max_price is not None:
            query = query.filter(ItemOrm.price <= max_price)

        # Apply pagination
        items_orm = query.offset(offset).limit(limit).all()

        return [
            Item(
                id=item.id,
                name=item.name,
                price=float(item.price),
                deleted=item.deleted
            )
            for item in items_orm
        ]

    def update_item(self, item_id: int, name: str, price: float) -> Item | None:
        item_orm = self.db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
        if not item_orm:
            return None
        item_orm.name = name
        item_orm.price = price
        self.db.commit()
        self.db.refresh(item_orm)
        return Item(
            id=item_orm.id,
            name=item_orm.name,
            price=float(item_orm.price),
            deleted=item_orm.deleted
        )

    def patch_item(self, item_id: int, name: str | None, price: float | None) -> Item | None:
        item_orm = self.db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
        if not item_orm:
            return None

        if item_orm.deleted:
            return None

        if name is not None:
            item_orm.name = name
        if price is not None:
            item_orm.price = price

        self.db.commit()
        self.db.refresh(item_orm)
        return Item(
            id=item_orm.id,
            name=item_orm.name,
            price=float(item_orm.price),
            deleted=item_orm.deleted
        )

    def delete_item(self, item_id: int) -> bool:
        item_orm = self.db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
        if item_orm:
            item_orm.deleted = True
            self.db.commit()
        return True

    def create_cart(self) -> int:
        cart_orm = CartOrm()
        self.db.add(cart_orm)
        self.db.commit()
        self.db.refresh(cart_orm)
        return cart_orm.id

    def get_cart(self, cart_id: int) -> Cart | None:
        cart_orm = self.db.query(CartOrm).filter(CartOrm.id == cart_id).first()
        if not cart_orm:
            return None

        cart_items_orm = self.db.query(CartItemOrm).filter(CartItemOrm.cart_id == cart_id).all()
        items = []
        total_price = 0.0

        for cart_item in cart_items_orm:
            item_orm = self.db.query(ItemOrm).filter(ItemOrm.id == cart_item.item_id).first()
            if item_orm:
                items.append(
                    CartItem(
                        id=item_orm.id,
                        name=item_orm.name,
                        quantity=cart_item.quantity,
                        available=not item_orm.deleted,
                    )
                )
                if not item_orm.deleted:
                    total_price += float(item_orm.price) * cart_item.quantity

        return Cart(id=cart_id, items=items, price=total_price)

    def get_carts(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        min_quantity: int | None = None,
        max_quantity: int | None = None,
    ) -> list[Cart]:
        cart_ids = self.db.query(CartOrm.id).offset(offset).limit(limit).all()
        carts = []

        for (cart_id,) in cart_ids:
            cart = self.get_cart(cart_id)
            if cart:
                # Apply filters
                if min_price is not None and cart.price < min_price:
                    continue
                if max_price is not None and cart.price > max_price:
                    continue

                total_quantity = sum(item.quantity for item in cart.items)
                if min_quantity is not None and total_quantity < min_quantity:
                    continue
                if max_quantity is not None and total_quantity > max_quantity:
                    continue

                carts.append(cart)

        return carts

    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        cart_orm = self.db.query(CartOrm).filter(CartOrm.id == cart_id).first()
        if not cart_orm:
            return False

        item_orm = self.db.query(ItemOrm).filter(ItemOrm.id == item_id).first()
        if not item_orm:
            return False

        cart_item = self.db.query(CartItemOrm).filter(
            CartItemOrm.cart_id == cart_id,
            CartItemOrm.item_id == item_id
        ).first()

        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = CartItemOrm(cart_id=cart_id, item_id=item_id, quantity=1)
            self.db.add(cart_item)

        self.db.commit()
        return True


# ==================== Item Endpoints ====================


@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(item_request: ItemCreateRequest, db: Session = Depends(get_db)) -> Item:
    """Создание нового товара"""
    storage = Storage(db)
    return storage.create_item(name=item_request.name, price=item_request.price)


@app.get("/item/{item_id}")
def get_item(item_id: int, db: Session = Depends(get_db)) -> Item:
    """Получение товара по id"""
    storage = Storage(db)
    item = storage.get_item(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@app.get("/item")
def get_items(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db),
) -> list[Item]:
    """Получение списка товаров с фильтрами"""
    storage = Storage(db)
    return storage.get_items(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )


@app.put("/item/{item_id}")
def update_item(item_id: int, item_request: ItemCreateRequest, db: Session = Depends(get_db)) -> Item:
    """Замена товара по id (только существующих)"""
    storage = Storage(db)
    item = storage.update_item(item_id, name=item_request.name, price=item_request.price)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@app.patch("/item/{item_id}")
def patch_item(item_id: int, patch_request: ItemPatchRequest, db: Session = Depends(get_db)) -> Item:
    """Частичное обновление товара по id"""
    storage = Storage(db)
    item = storage.patch_item(item_id, name=patch_request.name, price=patch_request.price)
    if not item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_MODIFIED, detail="Cannot modify deleted item"
        )
    return item


@app.delete("/item/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)) -> dict:
    """Удаление товара (пометка как deleted)"""
    storage = Storage(db)
    storage.delete_item(item_id)
    return {"message": "Item deleted"}


# ==================== Cart Endpoints ====================


@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response, db: Session = Depends(get_db)) -> CartResponse:
    """Создание новой корзины"""
    storage = Storage(db)
    cart_id = storage.create_cart()
    response.headers["location"] = f"/cart/{cart_id}"
    return CartResponse(id=cart_id)


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int, db: Session = Depends(get_db)) -> Cart:
    """Получение корзины по id"""
    storage = Storage(db)
    cart = storage.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return cart


@app.get("/cart")
def get_carts(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    min_quantity: Annotated[int | None, Query(ge=0)] = None,
    max_quantity: Annotated[int | None, Query(ge=0)] = None,
    db: Session = Depends(get_db),
) -> list[Cart]:
    """Получение списка корзин с фильтрами"""
    storage = Storage(db)
    return storage.get_carts(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)) -> Cart:
    """Добавление товара в корзину"""
    storage = Storage(db)
    success = storage.add_item_to_cart(cart_id, item_id)
    if not success:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Cart or item not found"
        )

    cart = storage.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

    return cart