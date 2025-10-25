"""
Store module - Data access layer using Data Mapper pattern.

This module provides:
- Domain models (dataclasses)
- ORM models (SQLAlchemy)
- Repositories (abstract interfaces and concrete implementations)
- Services (business logic)
- Dependencies (FastAPI dependency injection)
"""

# Domain Models
from .models import (
    CartEntity,
    CartInfo,
    CartItemEntity,
    ItemEntity,
    ItemInfo,
    PatchItemInfo,
)

# Database and ORM
from .database import (
    Base,
    ItemOrm,
    CartOrm,
    CartItemOrm,
    get_db,
    get_session,
    create_tables,
    drop_tables,
)

# Mappers
from .mappers import (
    ItemMapper,
    CartMapper,
)

# Interfaces
from .interface import (
    ItemRepositoryInterface,
    CartRepositoryInterface,
    ItemServiceInterface,
    CartServiceInterface,
)

# Repository Implementations
from .repositories import (
    SqlAlchemyItemRepository,
    SqlAlchemyCartRepository,
    InMemoryItemRepository,
    InMemoryCartRepository,
)

# Services
from .services import (
    ItemService,
    CartService,
    create_item_service,
    create_cart_service,
)

# FastAPI Dependencies
from .dependencies import (
    get_item_repository,
    get_cart_repository,
    get_item_service,
    get_cart_service,
)

# Legacy compatibility (deprecated - for backwards compatibility only)
# These import the old query functions but should not be used in new code
from .queries import (
    add_cart,
    add_item,
    add_item_to_cart,
    delete_item,
    get_cart,
    get_item,
    get_many_carts,
    get_many_items,
    patch_item,
    replace_item,
)

__all__ = [
    # Domain Models
    "CartEntity",
    "CartInfo",
    "CartItemEntity",
    "ItemEntity",
    "ItemInfo",
    "PatchItemInfo",
    # Database & ORM
    "Base",
    "ItemOrm",
    "CartOrm",
    "CartItemOrm",
    "get_db",
    "get_session",
    "create_tables",
    "drop_tables",
    # Mappers
    "ItemMapper",
    "CartMapper",
    # Interfaces
    "ItemRepositoryInterface",
    "CartRepositoryInterface",
    "ItemServiceInterface",
    "CartServiceInterface",
    # Repository Implementations
    "SqlAlchemyItemRepository",
    "SqlAlchemyCartRepository",
    "InMemoryItemRepository",
    "InMemoryCartRepository",
    # Services
    "ItemService",
    "CartService",
    "create_item_service",
    "create_cart_service",
    # FastAPI Dependencies
    "get_item_repository",
    "get_cart_repository",
    "get_item_service",
    "get_cart_service",
    # Legacy (deprecated)
    "add_cart",
    "add_item",
    "add_item_to_cart",
    "delete_item",
    "get_cart",
    "get_item",
    "get_many_carts",
    "get_many_items",
    "patch_item",
    "replace_item",
]
