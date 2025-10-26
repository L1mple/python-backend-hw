from __future__ import annotations

from typing import List

from pydantic import BaseModel, conint, conlist, confloat


class CartItemResponse(BaseModel):
    id: int
    quantity: int


class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float


class CartCreateResponse(BaseModel):
    id: int


class CartListQuery(BaseModel):
    offset: conint(ge=0) | None = None
    limit: conint(gt=0) | None = None
    min_price: confloat(ge=0) | None = None
    max_price: confloat(ge=0) | None = None
    min_quantity: conint(ge=0) | None = None
    max_quantity: conint(ge=0) | None = None