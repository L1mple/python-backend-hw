import uuid
from pydantic import BaseModel, ConfigDict


class ItemSchema(BaseModel):
    id: str = str(uuid.uuid4())
    name: str
    price: float
    deleted: bool = False
    quantity: int = 1


class ItemCreateSchema(BaseModel):
    name: str = ""
    price: float = 0.0


class ItemPatchSchema(BaseModel):
    name: str = ""
    price: float = 0.0
    quantity: int = 1

    model_config = ConfigDict(extra='forbid')
