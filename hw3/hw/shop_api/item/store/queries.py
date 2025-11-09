from typing import Iterable

from shop_api.item.store.models import ItemEntity, ItemInfo, PatchItemInfo


_data: dict[int, ItemInfo] = {}


def int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


_id_generator = int_id_generator()


def add(info: ItemInfo) -> ItemEntity:
    _id = next(_id_generator)
    _data[_id] = info

    return ItemEntity(_id, info)


def delete(id: int) -> None:
    if id in _data:
        del _data[id]


def get_one(id: int) -> ItemEntity | None:
    if id not in _data:
        return None

    return ItemEntity(id=id, info=_data[id])


def get_many(
    offset: int = 0,
    limit: int = 10,
    min_price: float = None,
    max_price: float = None,
    show_deleted: bool = False,
) -> Iterable[ItemEntity]:
    curr = 0
    for id, info in _data.items():
        if min_price is not None and min_price > info.price:
            continue
        if max_price is not None and max_price < info.price:
            continue

        if not show_deleted and info.deleted:
            continue

        if offset <= curr < offset + limit:
            yield ItemEntity(id, info)

        curr += 1


def update(id: int, info: ItemInfo) -> ItemEntity | None:
    if id not in _data:
        return None

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
