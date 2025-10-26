import uuid
from pydantic import BaseModel
from sqlalchemy import Column, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from shop_api.db.session import Base
from shop_api.models.item import ItemSchema 


class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    quantity = Column(Integer, default=1, nullable=False)

    cart_id = Column(PG_UUID(as_uuid=True), ForeignKey("carts.id"), nullable=False)
    item_id = Column(PG_UUID(as_uuid=True), ForeignKey("items.id"), nullable=False)
    
    cart = relationship("Cart", back_populates="cart_items")
    item = relationship("Item") 


class CartItemSchema(BaseModel):
    id: uuid.UUID
    quantity: int
    item: ItemSchema

    class Config:
        from_attributes = True
