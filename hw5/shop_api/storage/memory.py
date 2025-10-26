from typing import Dict
from threading import Lock
from shop_api.schemas.item import Item

_items: Dict[int, Item] = {}
_carts: Dict[int, Dict[int, int]] = {}
_next_item_id = 1
_next_cart_id = 1
_lock = Lock()
