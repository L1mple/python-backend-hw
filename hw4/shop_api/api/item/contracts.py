from pydantic import BaseModel, ConfigDict


class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

    class Config:
        from_attributes = True


class ItemRequest(BaseModel):
    name: str
    price: float
    deleted: bool = False


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")
