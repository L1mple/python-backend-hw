from pydantic import validate_call
from typing import Dict, List, Set, Union
from shop_api.models.cart import CartOutSchema
from shop_api.models.item import ItemSchema


_local_data_carts: Dict[str, CartOutSchema] = {}
_local_data_items: Dict[str, ItemSchema] = {}


@validate_call
def add_single_cart(cart_data: CartOutSchema) -> None:
    cart_id = cart_data.id
    _local_data_carts[cart_id] = cart_data


def get_single_cart(
        cart_id: str
) -> Union[CartOutSchema, None]:
    if cart_id not in _local_data_carts:
        return None

    return _local_data_carts[cart_id]


@validate_call
def get_all_carts() -> List[CartOutSchema]:
    return list(_local_data_carts.values())


@validate_call
def add_single_item(
        item_id: str,
        item_data: ItemSchema
) -> None:
    item_data.id = item_id
    _local_data_items[item_id] = item_data


@validate_call
def get_single_item(item_id: str) -> Union[ItemSchema, None]:
    if item_id not in _local_data_items:
        return None

    return _local_data_items[item_id]


@validate_call
def get_all_items() -> List[ItemSchema]:
    return list(_local_data_items.values())


def get_all_item_ids_for_cart(cart_id: str) -> Set[str]:
    return set(list(_local_data_carts[cart_id].model_fields.keys()))


def delete_item(item_id: str) -> None:
    item = _local_data_items.get(item_id)
    item.deleted = True
