from typing import List, Optional
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

from sqlalchemy import Column, ForeignKey, Integer

from sqlalchemy.orm import Session, relationship

from db.init import Base
from db.item import Item, ItemMapper, ItemRepositoryInterface


# === Доменные модели (без привязки к БД) ===

@dataclass
class CartItem:
    """Доменная модель корзины"""
    id: Optional[int] = None
    name: str = ""
    quantity: int = 0
    available: bool = True
    
    
@dataclass
class Cart:
    """Доменная модель корзины"""
    id: Optional[int] = None
    items: List[CartItem] = field(default_factory=list)  # Теперь храним просто товары
    price: float = 0


# === SQLAlchemy модели (для мапинга с БД) ===
    

class CartOrm(Base):
    __tablename__ = 'carts'

    id = Column(Integer, primary_key=True)
    orders = relationship("OrdersOrm", back_populates="cart")
    
    
class OrdersOrm(Base):
    __tablename__ = 'orders'

    id = Column(Integer, primary_key=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    item_id = Column(Integer, ForeignKey("items.id", ondelete="CASCADE"), nullable=False)

    # Relationships
    cart = relationship("CartOrm", back_populates="orders")
    item = relationship("ItemOrm")

# === Мапперы (преобразование между доменными моделями и ORM) ===

class CartMapper:
    """Маппер для преобразования между Cart и CartOrm"""

    @staticmethod
    def to_domain(orm_cart: CartOrm) -> Cart:
        """Преобразование ORM модели в доменную"""
        items = []
        tmp = {}
        
        # Каждая строка в orders представляет один экземпляр товара
        for order in orm_cart.orders:
            item = ItemMapper.to_domain(order.item)
            if item.id not in tmp:
                tmp[item.id] = {"name": item.name, "price": item.price, "quantity": 1, "available": not item.deleted}
            else:
                tmp[item.id]["quantity"] += 1
        
        total_price = 0
        for key, value in tmp.items():
            items.append(CartItem(id=key, name=value["name"], quantity=value["quantity"], available=value["available"]))
            total_price += value["price"] * value["quantity"]
        
        return Cart(
            id=orm_cart.id,
            items=items,
            price=total_price
        )

    @staticmethod
    def to_orm(
        domain_cart: Cart,
        orm_cart: Optional[CartOrm] = None,
    ) -> CartOrm:
        """Преобразование доменной модели в ORM"""
        if orm_cart is None:
            orm_cart = CartOrm()
        
        # Логика orders будет обрабатываться в репозитории
        return orm_cart

# === Абстрактные интерфейсы репозиториев ===

class CartRepositoryInterface(ABC):
    """Интерфейс репозитория корзин"""

    @abstractmethod
    def create(self, cart: Cart) -> Cart:
        pass

    @abstractmethod
    def find_by_id(self, cart_id: int) -> Optional[Cart]:
        pass

    @abstractmethod
    def update(self, cart: Cart) -> Cart:
        pass

    @abstractmethod
    def delete(self, cart_id: int) -> None:
        pass
        
    @abstractmethod
    def get_all(self) -> List[Cart]:
        pass


# === Конкретные реализации репозиториев ===

class SqlAlchemyCartRepository(CartRepositoryInterface):
    """SQLAlchemy реализация репозитория корзин"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, cart: Cart) -> Cart:
        orm_cart = CartMapper.to_orm(cart)
        self.session.add(orm_cart)
        self.session.flush()
        
        # Сохраняем items корзины как отдельные строки в orders
        for item in cart.items:
            order = OrdersOrm(cart_id=orm_cart.id, item_id=item.id)
            self.session.add(order)
        
        self.session.commit()
        return CartMapper.to_domain(orm_cart)

    def find_by_id(self, cart_id: int) -> Optional[Cart]:
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        return CartMapper.to_domain(orm_cart) if orm_cart else None

    def update(self, cart: Cart) -> Cart:
        orm_cart = self.session.query(CartOrm).filter_by(id=cart.id).first()
        if not orm_cart:
            raise ValueError(f"Cart with id {cart.id} not found")

        # Удаляем старые orders
        self.session.query(OrdersOrm).filter_by(cart_id=cart.id).delete()
        
        # Добавляем новые orders (каждый товар как отдельная строка)
        for item in cart.items:
            order = OrdersOrm(cart_id=cart.id, item_id=item.id)
            self.session.add(order)
        
        self.session.commit()
        return CartMapper.to_domain(orm_cart)

    def delete(self, cart_id: int) -> None:
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        if not orm_cart:
            raise ValueError(f"Cart with id {cart_id} not found")
        
        self.session.delete(orm_cart)
        self.session.commit()

    def get_all(self):
        orm_carts = self.session.query(CartOrm).all()
        return [CartMapper.to_domain(orm_cart) for orm_cart in orm_carts]

# === Сервисы для бизнес-логики ===

class CartService:
    """Сервис для работы с корзинами"""

    def __init__(self, cart_repo: CartRepositoryInterface, item_repo: ItemRepositoryInterface):
        self.cart_repo = cart_repo
        self.item_repo = item_repo

    def create_cart(self) -> Cart:
        """Создание новой корзины"""
        cart = Cart()
        return self.cart_repo.create(cart)
    
    def is_cart_exists(self, cart_id: int):
        cart = self.cart_repo.find_by_id(cart_id)
        return False if cart is None else True
    
    def get_cart(self, cart_id: int):
        cart = self.cart_repo.find_by_id(cart_id)
        
        if not cart:
            return None

        return cart
    
    def get_carts(self):
        return self.cart_repo.get_all()

    def add_item_to_cart(self, cart_id: int, item_id: int, count: int = 1) -> Cart:
        """Добавление товара в корзину"""
        if count <= 0:
            raise ValueError("Count must be positive")

        # Проверяем существование товара
        item = self.item_repo.find_by_id(item_id)
        if not item:
            raise ValueError(f"Item with id {item_id} not found")

        # Получаем корзину
        cart = self.cart_repo.find_by_id(cart_id)
        if not cart:
            raise ValueError(f"Cart with id {cart_id} not found")

        # Добавляем товар указанное количество раз (каждая копия - отдельная строка в orders)
        for _ in range(count):
            cart.items.append(item)

        return self.cart_repo.update(cart)


    def clear_cart(self, cart_id: int) -> Cart:
        """Очистка корзины"""
        cart = self.cart_repo.find_by_id(cart_id)
        if not cart:
            raise ValueError(f"Cart with id {cart_id} not found")

        cart.items = []
        return self.cart_repo.update(cart)