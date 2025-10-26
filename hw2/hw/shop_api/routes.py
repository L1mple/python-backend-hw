from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field, NonNegativeInt, PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from . import store
from .contracts import (
    CartResponse,
    ItemRequest,
    ItemResponse,
    PatchItemRequest,
    PutItemRequest,
)
from .database import get_db

router = APIRouter()


@router.post("/item", status_code=HTTPStatus.CREATED)
async def create_item(
    request: ItemRequest,
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    entity = await store.add_item(db, request.as_item_info())
    response.headers["location"] = f"/item/{entity.id}"
    return ItemResponse.from_entity(entity)


@router.get("/item/{item_id}")
async def get_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    entity = await store.get_item(db, item_id)
    if not entity or entity.info.deleted:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id {item_id} not found"
        )
    return ItemResponse.from_entity(entity)


@router.get("/item")
async def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    show_deleted: Annotated[bool, Query()] = False,
    db: AsyncSession = Depends(get_db)
) -> list[ItemResponse]:
    entities = await store.get_items_filtered(
        db,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )
    return [ItemResponse.from_entity(entity) for entity in entities]


@router.put("/item/{item_id}")
async def update_item(
    item_id: int,
    request: PutItemRequest,
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    entity = await store.update_item(db, item_id, request.as_item_info())
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id {item_id} not found"
        )
    return ItemResponse.from_entity(entity)


@router.patch("/item/{item_id}")
async def patch_item(
    item_id: int,
    request: PatchItemRequest,
    db: AsyncSession = Depends(get_db)
) -> ItemResponse:
    entity = await store.get_item(db, item_id)
    if not entity or entity.info.deleted:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Item with id {item_id} not found"
        )
    updated_entity = await store.patch_item(db, item_id, request.as_patch_item_info())
    return ItemResponse.from_entity(updated_entity)


@router.delete("/item/{item_id}")
async def delete_item(
    item_id: int,
    db: AsyncSession = Depends(get_db)
) -> Response:
    success = await store.delete_item(db, item_id)
    if not success:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id {item_id} not found"
        )
    return Response(status_code=HTTPStatus.OK)


@router.post("/cart", status_code=HTTPStatus.CREATED)
async def create_cart(
    response: Response,
    db: AsyncSession = Depends(get_db)
) -> dict[str, int]:
    entity = await store.add_cart(db)
    response.headers["location"] = f"/cart/{entity.id}"
    return {"id": entity.id}


@router.get("/cart/{cart_id}")
async def get_cart(
    cart_id: int,
    db: AsyncSession = Depends(get_db)
) -> CartResponse:
    entity = await store.get_cart(db, cart_id)
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id {cart_id} not found"
        )
    return CartResponse.from_entity(entity)


@router.get("/cart")
async def get_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    min_quantity: Annotated[int | None, Query(ge=0)] = None,
    max_quantity: Annotated[int | None, Query(ge=0)] = None,
    db: AsyncSession = Depends(get_db)
) -> list[CartResponse]:
    entities = await store.get_carts_filtered(
        db,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )
    return [CartResponse.from_entity(entity) for entity in entities]


@router.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(
    cart_id: int,
    item_id: int,
    db: AsyncSession = Depends(get_db)
) -> CartResponse:
    entity = await store.add_item_to_cart(db, cart_id, item_id)
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id {cart_id} or item with id {item_id} not found"
        )
    return CartResponse.from_entity(entity)
