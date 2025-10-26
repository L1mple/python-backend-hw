from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class ProductModel(Base):
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    cost = Column(Float, nullable=False)
    is_removed = Column(Boolean, default=False)

class BasketModel(Base):
    __tablename__ = 'baskets'
    
    id = Column(Integer, primary_key=True)
    total_cost = Column(Float, default=0.0)

class BasketProductModel(Base):
    __tablename__ = 'basket_products'
    
    id = Column(Integer, primary_key=True)
    basket_id = Column(Integer, ForeignKey('baskets.id'))
    product_id = Column(Integer, ForeignKey('products.id'))
    amount = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
