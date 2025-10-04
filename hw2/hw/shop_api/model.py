from typing import List, Optional
from pydantic import BaseModel
from fastapi import FastAPI, HTTPException
from sqlalchemy import Column, Integer, String, JSON, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from typing import Optional

Base = declarative_base()


class Item(BaseModel):
    id: Optional[int | None] = None
    name: str
    price: float
    deleted: Optional[bool] = False


class DBCart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    items = Column(JSON, default=[])  # Stores cart items as JSON
    price = Column(Float, nullable=True)  # Optional user association


class CartItem(BaseModel):
    id: int
    quantity: int


class Cart(BaseModel):
    id: int
    items: List[CartItem] = []
    price: float | None = 0


# First, create the DBItem model
class DBItem(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)
