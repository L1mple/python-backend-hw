from __future__ import annotations

from typing import Optional, Literal

from pydantic import BaseModel, Field


class ItemCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(gt=0)


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
    price: Optional[float] = Field(default=None, gt=0)
    # запрещаем обновление статуса deleted — тест ожидает 422
    deleted: Optional[Literal[False]] = Field(default=None)
    
    class Config:
        extra = "forbid"  # Запрещаем лишние поля - это вызовет 422 для {"odd": "value"}


class ItemListQuery(BaseModel):
    offset: Optional[int] = Field(None, ge=0)
    limit: Optional[int] = Field(None, gt=0)
    min_price: Optional[float] = Field(None, ge=0)
    max_price: Optional[float] = Field(None, ge=0)
    show_deleted: bool = Field(False)