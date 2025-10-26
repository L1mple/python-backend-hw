from datetime import datetime
from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserBase(BaseModel):
    email: str
    name: str
    age: int


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str
    price: float
    description: Optional[str] = None
    in_stock: bool = True


class ProductCreate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrderBase(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    status: str = 'pending'


class OrderCreate(OrderBase):
    pass


class OrderResponse(OrderBase):
    id: int
    total_price: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
