"""
Dependency injection for FastAPI routes.

This module provides FastAPI dependencies that create and manage
repositories and services with proper database session handling.
"""

from typing import Generator
from fastapi import Depends
from sqlalchemy.orm import Session

from .database import get_db
from .repositories import SqlAlchemyItemRepository, SqlAlchemyCartRepository
from .services import ItemService, CartService


# ============================================================================
# Repository Dependencies
# ============================================================================


def get_item_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyItemRepository:
    """
    FastAPI dependency to get an item repository.

    Args:
        db: Database session from get_db dependency

    Returns:
        Configured ItemRepository with database session
    """
    return SqlAlchemyItemRepository(db)


def get_cart_repository(
    db: Session = Depends(get_db),
) -> SqlAlchemyCartRepository:
    """
    FastAPI dependency to get a cart repository.

    Args:
        db: Database session from get_db dependency

    Returns:
        Configured CartRepository with database session
    """
    return SqlAlchemyCartRepository(db)


# ============================================================================
# Service Dependencies
# ============================================================================


def get_item_service(
    item_repo: SqlAlchemyItemRepository = Depends(get_item_repository),
) -> ItemService:
    """
    FastAPI dependency to get an item service.

    Args:
        item_repo: ItemRepository from get_item_repository dependency

    Returns:
        Configured ItemService
    """
    return ItemService(item_repo)


def get_cart_service(
    cart_repo: SqlAlchemyCartRepository = Depends(get_cart_repository),
    item_repo: SqlAlchemyItemRepository = Depends(get_item_repository),
) -> CartService:
    """
    FastAPI dependency to get a cart service.

    Args:
        cart_repo: CartRepository from get_cart_repository dependency
        item_repo: ItemRepository for item validation

    Returns:
        Configured CartService
    """
    return CartService(cart_repo, item_repo)


# ============================================================================
# Usage Example
# ============================================================================

"""
In your FastAPI routes, use these dependencies like this:

@router.post("/items")
def create_item(
    name: str,
    price: float,
    service: ItemService = Depends(get_item_service)
):
    return service.create_item(name, price)

The dependency injection system will:
1. Create a database session (get_db)
2. Create a repository with that session (get_item_repository)
3. Create a service with that repository (get_item_service)
4. Automatically commit/rollback and close the session after the request
"""
