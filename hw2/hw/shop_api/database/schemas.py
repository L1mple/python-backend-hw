from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from typing import Optional


class UserBase(BaseModel):
    email: EmailStr
    name: str
    age: int = Field(ge=0, description="Age must be non-negative")


class UserCreate(UserBase):
    pass


class UserResponse(UserBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProductBase(BaseModel):
    name: str
    price: float = Field(ge=0, description="Price must be non-negative")
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
    quantity: int = Field(ge=1, description="Quantity must be at least 1")
    status: str = 'pending'


class OrderCreate(OrderBase):
    pass


class OrderResponse(OrderBase):
    id: int
    total_price: float
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
