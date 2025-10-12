from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt

from .store import add, get_list, get_one, patch, update, upsert, delete as delete_q

from .contracts import (
    ItemResponse, ItemRequest, PatchItemRequest
)

router = APIRouter(prefix="/item")


def _get_entity_or_404(entity, resource_path: str, status_code: HTTPStatus = HTTPStatus.NOT_FOUND):
    if not entity:
        raise HTTPException(status_code, f"Request resource {resource_path} was not found")
    return entity


@router.get("/")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    show_deleted: Annotated[bool, Query()] = False,
) -> list[ItemResponse]:
    return [ItemResponse.from_entity(e) for e in get_list(offset, limit, min_price, max_price, show_deleted)]


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
async def get_item_by_id(id: int) -> ItemResponse:
    entity = _get_entity_or_404(get_one(id), f"/item/{id}")
    return ItemResponse.from_entity(entity)


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_item(info: ItemRequest, response: Response) -> ItemResponse:
    entity = add(info.as_item_info())

    response.headers["location"] = f"/item/{entity.id}"

    return ItemResponse.from_entity(entity)


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
async def patch_item(id: int, info: PatchItemRequest) -> ItemResponse:
    entity = _get_entity_or_404(patch(id, info.as_patch_item_info()), f"/item/{id}", HTTPStatus.NOT_MODIFIED)
    return ItemResponse.from_entity(entity)


@router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully updated or upserted item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify item as one was not found",
        },
    }
)
async def put_item(
    id: int,
    info: ItemRequest,
    upsert_flag: Annotated[bool, Query(alias="upsert")] = False,
) -> ItemResponse:
    entity = upsert(id, info.as_item_info()) if upsert_flag else update(id, info.as_item_info())
    if not upsert_flag:  # update может вернуть None, upsert - всегда возвращает entity
        entity = _get_entity_or_404(entity, f"/item/{id}", HTTPStatus.NOT_MODIFIED)
    return ItemResponse.from_entity(entity)


@router.delete("/{id}")
async def delete_item(id: int) -> Response:
    delete_q(id)
    return Response("")
