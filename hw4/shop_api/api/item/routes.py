from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from sqlalchemy.orm import Session
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat

from shop_api import store
from shop_api.database import get_db

from shop_api.api.item.contracts import ItemRequest, ItemResponse, PatchItemRequest


router = APIRouter(prefix="/item")


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_item(info: ItemRequest, response: Response, db: Session = Depends(get_db)) -> ItemResponse:
    entity = store.add_item(db, info)

    response.headers["location"] = f"/item/{entity.id}"

    return ItemResponse.from_orm(entity)


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
async def get_item_by_id(id: int, db: Session = Depends(get_db)) -> ItemResponse:
    entity = store.get_one_item(db, id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/{id} was not found",
        )

    return ItemResponse.from_orm(entity)


@router.get("/")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] = 0,
    max_price: Annotated[NonNegativeFloat, Query()] = 1e10,
    show_deleted: Annotated[bool, Query()] = False,
    db: Session = Depends(get_db)
) -> list[ItemResponse]:
    return [ItemResponse.from_orm(e) for e in store.get_many_items(db, offset, limit, min_price, max_price, show_deleted)]


@router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify item as one was not found",
        },
    }
)
async def put_item(
    id: int,
    info: ItemRequest,
    db: Session = Depends(get_db)
) -> ItemResponse:
    entity = store.update_item(db, id, info)

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_orm(entity)


@router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully patched item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify item as one was not found",
        },
    },
)
async def patch_item(id: int, info: PatchItemRequest, db: Session = Depends(get_db)) -> ItemResponse:
    entity = store.patch_item(db, id, info)

    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    return ItemResponse.from_orm(entity)


@router.delete("/{id}")
async def delete_item(id: int, db: Session = Depends(get_db)) -> Response:
    store.delete_item(db, id)
    return Response("")
