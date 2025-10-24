from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from sqlalchemy.orm import Session

from shop_api.db import get_db
from shop_api.item import store
from shop_api.item.contracts import ItemRequest, ItemResponse, PatchItemRequest

router = APIRouter(prefix="/item", tags=["Item"])


@router.post("/", status_code=HTTPStatus.CREATED)
async def post_item(
    info: ItemRequest,
    response: Response,
    db: Session = Depends(get_db)
) -> ItemResponse:
    entity = store.add(db, info.as_item_info())
    response.headers["Location"] = f"/item/{entity.id}"
    return ItemResponse.from_entity(entity)


@router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Успешно найден товар"},
        HTTPStatus.NOT_FOUND: {"description": "Товар не найден"},
    },
)
async def get_item_by_id(id: int, db: Session = Depends(get_db)) -> ItemResponse:
    entity = store.get_one(db, id)
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )
    return ItemResponse.from_entity(entity)


@router.get("/")
async def get_item_list(
    db: Session = Depends(get_db),
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] | None = None,
    max_price: Annotated[NonNegativeFloat, Query()] | None = None,
    show_deleted: Annotated[bool, Query()] = False,
):
    entities = store.get_many(
        db=db,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )
    return [ItemResponse.from_entity(e) for e in entities]


@router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Успешно обновлён товар (PATCH)"},
        HTTPStatus.NOT_FOUND: {"description": "Товар не найден"},
    },
)
async def patch_item(
    id: int,
    info: PatchItemRequest,
    db: Session = Depends(get_db),
) -> ItemResponse:
    entity = store.patch(db, id, info.as_patch_item_info())
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )
    return ItemResponse.from_entity(entity)


@router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Успешно обновлён товар (PUT)"},
        HTTPStatus.NOT_FOUND: {"description": "Товар не найден"},
    },
)
async def put_item(
    id: int,
    info: ItemRequest,
    db: Session = Depends(get_db),
) -> ItemResponse:
    entity = store.update(db, id, info.as_item_info())
    if entity is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )
    return ItemResponse.from_entity(entity)


@router.delete(
    "/{id}",
    status_code=HTTPStatus.NO_CONTENT,
    responses={
        HTTPStatus.NO_CONTENT: {"description": "Товар успешно удалён"},
        HTTPStatus.NOT_FOUND: {"description": "Товар не найден"},
    },
)
async def delete_item(id: int, db: Session = Depends(get_db)) -> Response:
    deleted = store.delete(db, id)
    if not deleted:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Requested resource /item/{id} was not found",
        )
    return Response(status_code=HTTPStatus.NO_CONTENT)
