from typing import Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict


class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)


class ItemUpdate(BaseModel):
    name: str
    price: float = Field(gt=0)


class ItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)

    @field_validator('price')
    @classmethod
    def validate_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Price must be positive')
        return v


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartResponse(BaseModel):
    id: int
    items: list[CartItemResponse]
    price: float
