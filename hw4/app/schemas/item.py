from pydantic import BaseModel, ConfigDict


class CreateItem(BaseModel):
    name: str
    price: float


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class UpdateItem(BaseModel):
    id: int | None = None
    name: str
    price: float
    deleted: bool | None = False


class PatchItem(BaseModel):
    id: int | None = None
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")
