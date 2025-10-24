from sqlalchemy import Column, Integer, Boolean, Float, String
from sqlalchemy.orm import relationship

from shop_api.db import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

    cart_items = relationship("CartItem", back_populates="item")
