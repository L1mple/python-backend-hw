from pydantic import BaseModel

class ItemBase(BaseModel):
    name: str
    price: float

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    deleted: bool = False

class ItemOut(ItemBase):
    id: int
    deleted: bool

    class Config:
        orm_mode = True
