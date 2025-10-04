from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ItemCreate(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemUpdate(BaseModel):
    name: str
    price: float = Field(ge=0)


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(default=None, ge=0)
    
    model_config = ConfigDict(extra="forbid")


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

    model_config = ConfigDict(from_attributes=True)
