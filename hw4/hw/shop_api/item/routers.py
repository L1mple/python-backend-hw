from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from sqlalchemy.orm import Session
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from shop_api.item import store
from shop_api.item.contracts import ItemRequest, ItemResponse, PatchItemRequest
from database import get_db

router = APIRouter(prefix="/item")


@router.post("/", status_code=HTTPStatus.CREATED)
async def post_item(
    info: ItemRequest, 
    response: Response, 
    db: Session = Depends(get_db)
) -> ItemResponse:
    entity = store.add(info.as_item_info(), db)
    response.headers["location"] = f"/item/{entity.id}"
    return ItemResponse.from_entity(entity)


@router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested item",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested item as one was not found",
        },
    },
)
async def get_item_by_id(
    id: int,
    db: Session = Depends(get_db)
):
    entity = store.get_one(id, db)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@router.get("/")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] | None = None,
    max_price: Annotated[NonNegativeFloat, Query()] | None = None,
    show_deleted: Annotated[bool, Query()] = False,
    db: Session = Depends(get_db)
):
    return [
        ItemResponse.from_entity(e)
        for e in store.get_many(db, offset, limit, min_price, max_price, show_deleted)
    ]


@router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully patched item",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to modify item as one was not found",
        },
    },
)
async def patch_item(
    id: int, 
    info: PatchItemRequest,
    db: Session = Depends(get_db)
) -> ItemResponse:
    entity = store.patch(id, info.as_patch_item_info(), db)

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated or upserted item",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to modify item as one was not found",
        },
    },
)
async def put_item(
    id: int,
    info: ItemRequest,
    db: Session = Depends(get_db)
) -> ItemResponse:
    entity = store.update(id, info.as_item_info(), db)

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_entity(entity)


@router.delete("/{id}")
async def delete_item(
    id: int,
    db: Session = Depends(get_db)
) -> Response:
    store.delete(id, db)
    return Response("", status_code=HTTPStatus.NO_CONTENT)