from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class ItemPut(BaseModel):
    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class ItemPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    price: float | None = Field(default=None, gt=0)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class ItemOut(BaseModel):
    id: int
    name: str
    price: float
    description: str | None = None
    deleted: bool = False

    model_config = ConfigDict(from_attributes=True)


@dataclass
class ItemRecord:
    name: str
    price: float
    description: str | None = None
    deleted: bool = False
