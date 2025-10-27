from fastapi import FastAPI, HTTPException, Query, Response, Depends
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from http import HTTPStatus
from dataclasses import dataclass, field
from abc import ABC, abstractmethod
import os
import time

from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship

app = FastAPI(title="Shop API")

# === Доменные модели (без привязки к БД) ===
@dataclass
class Item:
    id: int = 1
    name: str = ""
    price: float = 0.0
    deleted: bool = False

@dataclass
class ItemInCart:
    id: int = 1
    name: str = ""
    quantity: int = 0
    available: bool = True

@dataclass
class Cart:
    id: int = 1
    items: List[ItemInCart] = field(default_factory=list)
    price: float = 0.0

# === Pydantic модели ===
class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

class ItemInCartResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: List[ItemInCartResponse] = []
    price: float

class ItemCreatingObj(BaseModel):
    name: str
    price: float = Field(..., gt=0)

class ItemUpdatingObj(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)

    model_config = ConfigDict(extra="forbid")

# === SQLAlchemy модели (для мапинга с БД) ===
Base = declarative_base()

class ItemOrm(Base):
    __tablename__ = 'items'
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

class ItemInCartOrm(Base):
    __tablename__ = 'items_in_cart'
    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    name = Column(String(255), nullable=False)
    quantity = Column(Integer, nullable=False)
    available = Column(Boolean, default=True)
    cart = relationship("CartOrm", back_populates="items")

class CartOrm(Base):
    __tablename__ = 'carts'
    id = Column(Integer, primary_key=True)
    price = Column(Float, default=0.0)
    items = relationship("ItemInCartOrm", back_populates="cart", cascade="all, delete-orphan")

# === Мапперы (преобразование между доменными моделями и ORM) ===
class ItemMapper:
    """Маппер для преобразования между Item и ItemOrm"""
    @staticmethod
    def to_domain(orm_item: ItemOrm) -> Item:
        """Преобразование ORM модели в доменную"""
        return Item(id=orm_item.id, name=orm_item.name, price=orm_item.price, deleted=orm_item.deleted)
    
    @staticmethod
    def to_orm(domain_item: Item, orm_item: Optional[ItemOrm] = None) -> ItemOrm:
        """Преобразование доменной модели в ORM"""
        if orm_item is None:
            orm_item = ItemOrm()
        orm_item.name = domain_item.name
        orm_item.price = domain_item.price
        orm_item.deleted = domain_item.deleted
        return orm_item
    
class ItemInCartMapper:
    """Маппер для преобразования между ItemInCart и ItemInCartOrm"""
    @staticmethod
    def to_domain(orm_item: ItemInCartOrm) -> ItemInCart:
        """Преобразование ORM модели в доменную"""
        return ItemInCart(id=orm_item.item_id, name=orm_item.name, quantity=orm_item.quantity, available=orm_item.available)

    @staticmethod
    def to_orm(domain_item: ItemInCart, orm_item: Optional[ItemInCartOrm] = None) -> ItemInCartOrm:
        """Преобразование доменной модели в ORM"""
        if orm_item is None:
            orm_item = ItemInCartOrm()
        orm_item.item_id = domain_item.id
        orm_item.name = domain_item.name
        orm_item.quantity = domain_item.quantity
        orm_item.available = domain_item.available
        return orm_item
    
class CartMapper:
    """Маппер для преобразования между Cart и CartOrm"""
    @staticmethod
    def to_domain(orm_cart: CartOrm) -> Cart:
        """Преобразование ORM модели в доменную"""
        items = [ItemInCartMapper.to_domain(item) for item in orm_cart.items]
        return Cart(id=orm_cart.id, items=items, price=orm_cart.price)
    
    @staticmethod
    def to_orm(domain_cart: Cart, orm_cart: Optional[CartOrm] = None) -> CartOrm:
        """Преобразование доменной модели в ORM"""
        if orm_cart is None:
            orm_cart = CartOrm()
        orm_cart.price = domain_cart.price
        return orm_cart
    
# === Абстрактные интерфейсы репозиториев ===
class ItemRepositoryInterface(ABC):
    """Интерфейс репозитория товаров"""
    @abstractmethod
    def create(self, item: Item) -> Item:
        pass
    @abstractmethod
    def find_by_id(self, item_id: int) -> Optional[Item]:
        pass
    @abstractmethod
    def get_all(self, offset: int, limit: int, min_price: Optional[float], max_price: Optional[float], show_deleted: bool) -> List[Item]:
        pass
    @abstractmethod
    def update(self, item: Item) -> Item:
        pass
    @abstractmethod
    def delete(self, item_id: int) -> None:
        pass

class CartRepositoryInterface(ABC):
    """Интерфейс репозитория корзин"""
    @abstractmethod
    def create(self) -> Cart:
        pass
    @abstractmethod
    def find_by_id(self, cart_id: int) -> Optional[Cart]:
        pass
    @abstractmethod
    def get_all(self, offset: int, limit: int, min_price: Optional[float], max_price: Optional[float], min_quantity: Optional[int], max_quantity: Optional[int]) -> List[Cart]:
        pass
    @abstractmethod
    def add_item(self, cart_id: int, item_id: int) -> Cart:
        pass

# === Конкретные реализации репозиториев ===
class SqlAlchemyItemRepository(ItemRepositoryInterface):
    """SQLAlchemy реализация репозитория товаров"""
    def __init__(self, session: Session):
        self.session = session

    def create(self, item: Item) -> Item:
        orm_item = ItemMapper.to_orm(item)
        self.session.add(orm_item)
        self.session.flush()
        return ItemMapper.to_domain(orm_item)

    def find_by_id(self, item_id: int) -> Optional[Item]:
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        return ItemMapper.to_domain(orm_item) if orm_item else None

    def get_all(self, offset: int, limit: int, min_price: Optional[float], max_price: Optional[float], show_deleted: bool) -> List[Item]:
        query = self.session.query(ItemOrm)
        if not show_deleted:
            query = query.filter_by(deleted=False)
        if min_price is not None:
            query = query.filter(ItemOrm.price >= min_price)
        if max_price is not None:
            query = query.filter(ItemOrm.price <= max_price)
        orm_items = query.offset(offset).limit(limit).all()
        return [ItemMapper.to_domain(item) for item in orm_items]

    def update(self, item: Item) -> Item:
        orm_item = self.session.query(ItemOrm).filter_by(id=item.id).first()
        if not orm_item:
            raise ValueError(f"Item with id {item.id} not found")
        old_price = orm_item.price
        ItemMapper.to_orm(item, orm_item)
        orm_cart_items = self.session.query(ItemInCartOrm).filter_by(item_id=item.id).all()
        for cart_item in orm_cart_items:
            orm_cart = self.session.query(CartOrm).filter_by(id=cart_item.cart_id).first()
            orm_cart.price += (item.price - old_price) * cart_item.quantity
        self.session.flush()
        return ItemMapper.to_domain(orm_item)

    def delete(self, item_id: int) -> None:
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        if not orm_item:
            raise ValueError(f"Item with id {item_id} not found")
        orm_item.deleted = True
        for orm_cart_item in self.session.query(ItemInCartOrm).filter_by(item_id=item_id).all():
            orm_cart_item.available = False
            orm_cart = self.session.query(CartOrm).filter_by(id=orm_cart_item.cart_id).first()
            orm_cart.price -= orm_cart_item.quantity * orm_item.price
        self.session.flush()

class SqlAlchemyCartRepository(CartRepositoryInterface):
    """SQLAlchemy реализация репозитория корзин"""
    def __init__(self, session: Session):
        self.session = session

    def create(self) -> Cart:
        orm_cart = CartOrm(price=0.0)
        self.session.add(orm_cart)
        self.session.flush()
        return CartMapper.to_domain(orm_cart)

    def find_by_id(self, cart_id: int) -> Optional[Cart]:
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        return CartMapper.to_domain(orm_cart) if orm_cart else None

    def get_all(self, offset: int, limit: int, min_price: Optional[float], max_price: Optional[float], min_quantity: Optional[int], max_quantity: Optional[int]) -> List[Cart]:
        from sqlalchemy.sql import func
        query = self.session.query(CartOrm)
        if min_price is not None:
            query = query.filter(CartOrm.price >= min_price)
        if max_price is not None:
            query = query.filter(CartOrm.price <= max_price)
        if min_quantity is not None or max_quantity is not None:
            query = query.join(ItemInCartOrm).group_by(CartOrm.id)
            if min_quantity is not None:
                query = query.having(func.sum(ItemInCartOrm.quantity) >= min_quantity)
            if max_quantity is not None:
                query = query.having(func.sum(ItemInCartOrm.quantity) <= max_quantity)
        orm_carts = query.offset(offset).limit(limit).all()
        return [CartMapper.to_domain(cart) for cart in orm_carts]

    def add_item(self, cart_id: int, item_id: int) -> Cart:
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        if not orm_cart:
            raise ValueError(f"Cart with id {cart_id} not found")
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        if not orm_item or orm_item.deleted:
            raise ValueError(f"Item with id {item_id} not found")
        
        for cart_item in orm_cart.items:
            if cart_item.item_id == item_id:
                cart_item.quantity += 1
                orm_cart.price += orm_item.price
                self.session.flush()
                return CartMapper.to_domain(orm_cart)

        orm_cart_item = ItemInCartOrm(cart_id=cart_id, item_id=item_id, name=orm_item.name, quantity=1, available=True)
        orm_cart.items.append(orm_cart_item)
        orm_cart.price += orm_item.price
        self.session.flush()
        return CartMapper.to_domain(orm_cart)
    
# === Инициализация БД ===
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:password@db:5432/shop_db")
time.sleep(5)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# === Эндпоинты ===
@app.post("/cart", response_model=dict, status_code=HTTPStatus.CREATED)
async def create_cart(response: Response, db: Session = Depends(get_db)):
    repo = SqlAlchemyCartRepository(db)
    cart = repo.create()
    response.headers["location"] = f"/cart/{cart.id}"
    db.commit()
    return {"id": cart.id}

@app.get("/cart/{id}", response_model=CartResponse)
async def get_cart(id: int, db: Session = Depends(get_db)):
    repo = SqlAlchemyCartRepository(db)
    cart = repo.find_by_id(id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return cart

@app.get("/cart", response_model=List[CartResponse])
async def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db)
):
    repo = SqlAlchemyCartRepository(db)
    return repo.get_all(offset, limit, min_price, max_price, min_quantity, max_quantity)

@app.post("/cart/{cart_id}/add/{item_id}", response_model=CartResponse)
async def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    repo = SqlAlchemyCartRepository(db)
    try:
        cart = repo.add_item(cart_id, item_id)
        db.commit()
        return cart
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(e))

@app.post("/item", response_model=ItemResponse, status_code=HTTPStatus.CREATED)
async def create_item(item: ItemCreatingObj, db: Session = Depends(get_db)):
    repo = SqlAlchemyItemRepository(db)
    domain_item = Item(name=item.name, price=item.price)
    created_item = repo.create(domain_item)
    db.commit()
    return created_item

@app.get("/item/{id}", response_model=ItemResponse)
async def get_item(id: int, db: Session = Depends(get_db)):
    repo = SqlAlchemyItemRepository(db)
    item = repo.find_by_id(id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item

@app.get("/item", response_model=List[ItemResponse])
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
    db: Session = Depends(get_db)
):
    repo = SqlAlchemyItemRepository(db)
    return repo.get_all(offset, limit, min_price, max_price, show_deleted)

@app.put("/item/{id}", response_model=ItemResponse)
async def update_item(id: int, item: ItemCreatingObj, db: Session = Depends(get_db)):
    repo = SqlAlchemyItemRepository(db)
    domain_item = Item(id=id, name=item.name, price=item.price)
    try:
        updated_item = repo.update(domain_item)
        db.commit()
        return updated_item
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(e))

@app.patch("/item/{id}", response_model=ItemResponse)
async def partial_update_item(id: int, item: ItemUpdatingObj, db: Session = Depends(get_db)):
    repo = SqlAlchemyItemRepository(db)
    existing_item = repo.find_by_id(id)
    if not existing_item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    if existing_item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED, detail="Item is deleted")
    domain_item = Item(id=id, name=item.name or existing_item.name, price=item.price or existing_item.price, deleted=existing_item.deleted)
    updated_item = repo.update(domain_item)
    db.commit()
    return updated_item

@app.delete("/item/{id}", response_model=dict)
async def delete_item(id: int, db: Session = Depends(get_db)):
    repo = SqlAlchemyItemRepository(db)
    try:
        repo.delete(id)
        db.commit()
        return {"status_code": HTTPStatus.OK}
    except ValueError as e:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(e))