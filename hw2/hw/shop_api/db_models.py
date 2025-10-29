from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.sql import func
from datetime import datetime

Base = declarative_base()

class ItemDB(Base):
    __tablename__ = 'items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)
    created_at = Column(String, default=func.now())
    
    cart_items = relationship("CartItemDB", back_populates="item")
    
    def to_pydantic(self):
        from models import Item
        return Item(
            id=self.id,
            name=self.name,
            price=self.price,
            deleted=self.deleted
        )

class CartDB(Base):
    __tablename__ = 'carts'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(String, default=func.now())
    
    items = relationship("CartItemDB", back_populates="cart", cascade="all, delete-orphan")
    
    def to_pydantic(self):
        from models import Cart
        items_dict = {cart_item.item_id: cart_item.quantity for cart_item in self.items}
        return Cart(
            id=self.id,
            items=items_dict
        )
    
    def create_cart_response(self, items_dict: dict):
        from models import CartResponse, CartResponseItem
        
        price = 0.0
        total_quantity = 0
        prepared_items = []

        for cart_item in self.items:
            item = items_dict.get(cart_item.item_id)
            if item:
                total_quantity += cart_item.quantity
                price += item.price * cart_item.quantity
                prepared_items.append(
                    CartResponseItem(
                        id=item.id,
                        name=item.name,
                        quantity=cart_item.quantity,
                        available=(not item.deleted),
                    )
                )

        return CartResponse(
            id=self.id, 
            items=prepared_items, 
            price=price
        ), total_quantity

class CartItemDB(Base):
    __tablename__ = 'cart_items'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    cart_id = Column(Integer, ForeignKey('carts.id'), nullable=False)
    item_id = Column(Integer, ForeignKey('items.id'), nullable=False)
    quantity = Column(Integer, default=1)

    cart = relationship("CartDB", back_populates="items")
    item = relationship("ItemDB", back_populates="cart_items")