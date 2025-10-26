from __future__ import annotations

from functools import lru_cache

from .repositories import CartRepository, ItemRepository
from .services import CartService, ItemService


@lru_cache
def get_item_repository() -> ItemRepository:
    return ItemRepository()


@lru_cache
def get_cart_repository() -> CartRepository:
    return CartRepository(get_item_repository())


def get_item_service() -> ItemService:
    return ItemService(get_item_repository())


def get_cart_service() -> CartService:
    item_repo = get_item_repository()
    cart_repo = get_cart_repository()
    return CartService(cart_repo, item_repo)