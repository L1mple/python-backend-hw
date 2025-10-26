from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, conbool, confloat, conint


class ItemCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    price: confloat(gt=0)


class ItemCreateResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class ItemResponse(ItemCreateResponse):
    ...


class ItemUpdateRequest(ItemCreateRequest):
    ...


class ItemPatchRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1)
    price: Optional[confloat(gt=0)] = None
    # запрещаем обновление статуса deleted — тест ожидает 422
    deleted: Optional[conbool(strict=True)] = Field(default=None, const=False)


class ItemListQuery(BaseModel):
    offset: conint(ge=0) | None = None
    limit: conint(gt=0) | None = None
    min_price: confloat(ge=0) | None = None
    max_price: confloat(ge=0) | None = None
    show_deleted: bool = False