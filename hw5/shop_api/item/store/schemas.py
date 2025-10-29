from pydantic import BaseModel
from typing import Optional


class ItemInfo(BaseModel):
    name: str
    price: float
    deleted: bool = False

    class Config:
        from_attributes = True


class PatchItemInfo(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    class Config:
        from_attributes = True


class ItemEntity(BaseModel):
    id: int
    info: ItemInfo

    class Config:
        from_attributes = True