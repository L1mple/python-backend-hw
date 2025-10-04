from typing import Optional, List

from store.models import Item
from store.queries.utils import id_generator



data_item = dict[int, Item]()
item_id_generator = id_generator()


def add_item(
        name: str,
        price: float
) -> Item:
    new_item_id = next(item_id_generator)
    new_item = Item(new_item_id, name, price, False)
    data_item[new_item_id] = new_item
    return new_item


def delete_item(item_id: int) -> Item | None:
    if item_id not in data_item:
        return None

    data_item[item_id].deleted = True
    return data_item[item_id]


def get_item_by_id(id: int) -> Item | None:
    if not id in data_item:
        return None

    item = data_item[id]

    if item.deleted:
        return None

    return data_item[id]


def list_items(
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: Optional[bool] = False
) -> List[Item] | None:

    items = list(data_item.values())
    if show_deleted is not None and show_deleted is False:
        items = [item for item in items if not item.deleted]

    if min_price is not None:
        items = [item for item in items if item.price >= min_price]

    if max_price is not None:
        items = [item for item in items if item.price <= max_price]

    offset = offset or 0
    limit = limit or len(items)

    return items[offset:offset + limit]

def update_item_full(
        item_id: int,
        name: Optional[str] = None,
        price: Optional[float] = None,
        deleted: Optional[bool] = None,
) -> Item | None:
    if not item_id in data_item:
        return None

    if name:
        data_item[item_id].name = name

    if price:
        data_item[item_id].price = price

    if deleted is not None:
        data_item[item_id].deleted = deleted

    return data_item[item_id]


def update_item_partial(
        item_id: int,
        name: Optional[str] = None,
        price: Optional[float] = None
) -> Item | None:

    if item_id not in data_item:
        return None

    if name:
        data_item[item_id].name = name

    if price:
        data_item[item_id].price = price

    return data_item[item_id]