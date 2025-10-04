from pydantic import BaseModel


class ItemPostRequest(BaseModel):
    name: str
    price: float


class ItemPutRequest(BaseModel):
    name: str
    price: float


class ItemPatchRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = {
        "extra": "forbid",
    }
