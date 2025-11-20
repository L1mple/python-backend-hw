from typing import Iterable
from itertools import count

from .models import (
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)

_data: dict[int, ItemInfo] = {}

_id_generator = count()


def add(info: ItemInfo) -> ItemEntity:
    _id = next(_id_generator)
    _data[_id] = info

    return ItemEntity(_id, info)


def delete(id: int) -> None:
    _data.pop(id, None)


def get_one(id: int) -> ItemEntity | None:
    info = _data.get(id)
    return ItemEntity(id=id, info=info) if info else None


def get_list(offset: int = 0, limit: int = 10, min_price: float | None = None, max_price: float | None = None, show_deleted: bool = False) -> Iterable[ItemEntity]:
    def matches_filters(info: ItemInfo) -> bool:
        if min_price is not None and info.price < min_price:
            return False
        if max_price is not None and info.price > max_price:
            return False
        if not show_deleted and info.deleted:
            return False
        return True
    
    filtered_items = [ItemEntity(id, info) for id, info in _data.items() if matches_filters(info)]
    return filtered_items[offset:offset+limit]
    


def update(id: int, info: ItemInfo) -> ItemEntity | None:
    if id not in _data:
        return None
    _data[id] = info
    return ItemEntity(id=id, info=info)


def upsert(id: int, info: ItemInfo) -> ItemEntity:
    _data[id] = info
    return ItemEntity(id=id, info=info)


def patch(id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    if id not in _data:
        return None

    if patch_info.name is not None:
        _data[id].name = patch_info.name

    if patch_info.price is not None:
        _data[id].price = patch_info.price

    return ItemEntity(id=id, info=_data[id])
