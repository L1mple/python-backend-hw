import uuid
from typing import List
from pydantic import BaseModel, Field, computed_field

from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from shop_api.db.session import Base
from shop_api.models.cart_item import CartItemSchema 


class Cart(Base):
    __tablename__ = "carts"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    cart_items = relationship(
        "CartItem",
        back_populates="cart",
        cascade="all, delete-orphan"
    )


class CartOutSchema(BaseModel):
    id: uuid.UUID
    items: List[CartItemSchema] = Field(default_factory=list) 

    @computed_field
    @property
    def price(self) -> float:
        return sum(cart_item.item.price * cart_item.quantity for cart_item in self.items)

    class Config:
        from_attributes = True
