from sqlalchemy import Column, Integer, String, Float, Boolean
from database import Base

class ItemDB(Base):
    __tablename__ = "items"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

from dataclasses import dataclass

@dataclass(slots=True)
class ItemInfo:
    name: str
    price: float
    deleted: bool

@dataclass(slots=True)
class ItemEntity:
    id: int
    info: ItemInfo

@dataclass(slots=True)
class PatchItemInfo:
    name: str | None = None
    price: float | None = None