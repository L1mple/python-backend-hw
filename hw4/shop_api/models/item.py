import uuid
from pydantic import BaseModel, ConfigDict

from sqlalchemy import Column, String, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from shop_api.db.session import Base


class Item(Base):
    __tablename__ = "items"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False, index=True)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False, nullable=False, index=True)


class ItemSchema(BaseModel):
    id: uuid.UUID
    name: str
    price: float
    deleted: bool = False
    
    class Config:
        from_attributes = True


class ItemCreateSchema(BaseModel):
    name: str = ""
    price: float = 0.0

class ItemPatchSchema(BaseModel):
    name: str = ""
    price: float = 0.0

    model_config = ConfigDict(extra='forbid')