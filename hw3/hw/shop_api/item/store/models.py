from dataclasses import dataclass


@dataclass(slots=True)
class ItemInfo:
    name: str
    price: float
    deleted: bool


@dataclass(slots=True)
class ItemEntity:
    id: int
    info: ItemInfo


@dataclass(slots=True)
class PatchItemInfo:
    name: str | None = None
    price: float | None = None