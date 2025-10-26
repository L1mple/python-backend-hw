from sqlalchemy import Column, Integer, String, Boolean, Numeric, ForeignKey, Table
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import relationship

base = declarative_base()

cart_items = Table(
    'cart_items',
    base.metadata,
    Column('cart_id', Integer, ForeignKey('carts.id'), primary_key=True),
    Column('item_id', Integer, ForeignKey('items.id'), primary_key=True),
    Column('quantity', Integer, nullable=False, default=1)
)

class Item(base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    deleted = Column(Boolean, default=False)
    
    items = relationship("Item", secondary=cart_items, back_populates="carts")
    carts = relationship("Cart", secondary=cart_items, back_populates="items")

class Cart(base):
    __tablename__ = "carts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    cart_item_associations = relationship("CartItemAssociation", back_populates="cart")

class CartItemAssociation(base):
    __tablename__ = "cart_items"
    __table_args__ = {'extend_existing': True}
    
    cart_id = Column(Integer, ForeignKey('carts.id'), primary_key=True)
    item_id = Column(Integer, ForeignKey('items.id'), primary_key=True)
    quantity = Column(Integer, nullable=False, default=1)
    
    cart = relationship("Cart", back_populates="cart_item_associations")
    item = relationship("Item", back_populates="cart_associations")
