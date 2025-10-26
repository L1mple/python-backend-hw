from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey
from sqlalchemy.orm import declarative_base

base = declarative_base()

class Item(base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    deleted = Column(Boolean, default=False)

class Cart(base):
    __tablename__ = "carts"
    
    id = Column(Integer, primary_key=True, index=True)


class CartItemAssociation(base):
    __tablename__ = "cart_items"
    
    cart_id = Column(Integer, ForeignKey('carts.id'), primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), primary_key=True)
    quantity = Column(Integer, nullable=False, default=1)