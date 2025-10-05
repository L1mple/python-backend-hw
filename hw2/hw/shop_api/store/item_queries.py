from typing import Iterable

from hw2.hw.shop_api.store.item_models import (
    PatchItemInfo,
    ItemEntity,
    ItemInfo,
)

from hw2.hw.shop_api.store.id_generator import id_generator

items_data = dict[int,ItemInfo]()

def add(info: ItemInfo) -> ItemEntity:
    _id = next(id_generator)
    items_data[_id] = info

    return ItemEntity(_id, info)


def delete(id: int) -> None:
    if id in items_data:
        # soft delete
        items_data[id].deleted = True


def get_one(id: int) -> ItemEntity | None:
    info = items_data.get(id)
    if info is None or info.deleted:
        return None
    return ItemEntity(id=id, info=info)


def get_many(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> Iterable[ItemEntity]:
    curr = 0
    for id, info in items_data.items():
        if (not show_deleted) and info.deleted:
            continue
        if min_price is not None and info.price < min_price:
            continue
        if max_price is not None and info.price > max_price:
            continue
        if offset <= curr < offset + limit:
            yield ItemEntity(id, info)
        curr += 1


def update(id: int, info: ItemInfo) -> ItemEntity | None:
    if id not in items_data or items_data[id].deleted:
        return None

    items_data[id] = info

    return ItemEntity(id=id, info=info)


def upsert(id: int, info: ItemInfo) -> ItemEntity:
    items_data[id] = info
    return ItemEntity(id=id, info=info)


def patch(id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    if id not in items_data or items_data[id].deleted:
        return None

    if patch_info.name is not None:
        items_data[id].name = patch_info.name

    if patch_info.price is not None:
        items_data[id].price = patch_info.price

    return ItemEntity(id=id, info=items_data[id])

