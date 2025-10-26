from functools import lru_cache
from shop_api.repositories import ItemRepository, CartRepository
from shop_api.services import ItemService, CartService
from shop_api.database import get_connection


@lru_cache
def get_item_repository() -> ItemRepository:
    return ItemRepository(get_connection())


@lru_cache
def get_cart_repository() -> CartRepository:
    return CartRepository(get_connection(), get_item_repository())  # передаем и connection, и item_repo


@lru_cache
def get_item_service() -> ItemService:
    return ItemService(get_item_repository())


@lru_cache
def get_cart_service() -> CartService:
    return CartService(get_cart_repository(), get_item_repository())