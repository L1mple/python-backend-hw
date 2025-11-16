import uuid
from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from shop_api.db.session import Base
from pydantic import BaseModel


class Product(Base):
    __tablename__ = "products"
    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)


class ProductSchema(BaseModel):
    id: str
    name: str
    price: float

    class Config:
        from_attributes = True


class ProductCreateSchema(BaseModel):
    name: str
    price: float
