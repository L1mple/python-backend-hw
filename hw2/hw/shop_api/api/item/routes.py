from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat
from sqlalchemy.orm import Session

from shop_api import store

from .contracts import (
    ItemMapper,
    ItemResponse,
    ItemRequest,
    ItemRequest,
    PatchItemRequest
)

item_router = APIRouter(prefix="/item")


@item_router.get("/")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    show_deleted: Annotated[bool, Query()] = False, 
    db: Session = Depends(store.get_db)
) -> list[ItemResponse]:
    return [ItemMapper.to_domain(orm_item) for orm_item in store.get_items(db, offset, limit, min_price, max_price, show_deleted)]


@item_router.get(
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
async def get_item_by_id(id: int, db: Session = Depends(store.get_db)) -> ItemResponse:
    orm_item = store.get_item(db, id)

    if not orm_item:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/{id} was not found",
        )

    return ItemMapper.to_domain(orm_item)


@item_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_item(info: ItemRequest, response: Response, db: Session = Depends(store.get_db)) -> ItemResponse:
    orm_item = store.add_item(db, ItemMapper.to_orm(info))

    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/item/{orm_item.id}"

    return ItemMapper.to_domain(orm_item)


@item_router.patch(
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
async def patch_item(id: int, info: PatchItemRequest, db: Session = Depends(store.get_db)) -> ItemResponse:
    orm_item = store.patch_item(db, id, info.name, info.price)

    if orm_item is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )

    return ItemMapper.to_domain(orm_item)


@item_router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated or upserted pokemon",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify pokemon as one was not found",
        },
    }
)
async def put_item(
    id: int,
    info: ItemRequest,
    db: Session = Depends(store.get_db)
) -> ItemResponse:
    orm_item = store.update_item(db, id, info.name, info.price, info.deleted)

    if orm_item is None:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Requested resource /item/{id} was not found",
        )
    
    return ItemMapper.to_domain(orm_item)


@item_router.delete("/{id}")
async def delete_item(id: int, db: Session = Depends(store.get_db)) -> Response:

    store.delete_item(db, id)

    return Response("")