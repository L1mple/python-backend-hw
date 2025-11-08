from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, Float, Boolean
from sqlalchemy.orm import relationship

from .database import Base


class Item(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)
    
    # Связь с элементами корзины
    cart_items = relationship("CartItem", back_populates="item")


class Cart(Base):
    """Модель корзины"""
    __tablename__ = "carts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Связь с элементами корзины
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    
    @property
    def price(self):
        """Вычисление общей суммы корзины"""
        return sum(cart_item.total_price for cart_item in self.items)
    
    # @property
    # def quantity(self):
    #     """Вычисление общей суммы корзины"""
    #     return sum(cart_item.quantity for cart_item in self.items)
    


class CartItem(Base):
    """Промежуточная таблица для связи корзины и товаров с количеством"""
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    quantity = Column(Integer, nullable=False, default=1)
    
    # Связи
    cart = relationship("Cart", back_populates="items")
    item = relationship("Item", back_populates="cart_items")
    
    @property
    def total_price(self):
        """Общая цена для данного товара в корзине (цена * количество)"""
        return self.item.price * self.quantity
