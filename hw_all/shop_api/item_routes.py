from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt
from sqlalchemy.orm import Session

from . import store
from .contracts import ItemMapper, ItemRequest, ItemResponse, PatchItemRequest
from .database import get_session

router = APIRouter(prefix="/item", tags=["item"])


@router.post("/", status_code=HTTPStatus.CREATED)
@router.post("", status_code=HTTPStatus.CREATED)
async def create_item(
    item_request: ItemRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> ItemResponse:
    orm_item = store.add_item(session, ItemMapper.to_orm(item_request))
    response.headers["location"] = f"/item/{orm_item.id}"
    return ItemMapper.to_domain(orm_item)


@router.get("/{id}")
async def get_item_by_id(
    id: int, session: Session = Depends(get_session)
) -> ItemResponse:
    orm_item = store.get_item(session, id)
    if not orm_item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item with id={id} not found",
        )
    return ItemMapper.to_domain(orm_item)


@router.get("/")
@router.get("")
async def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    show_deleted: bool = False,
    session: Session = Depends(get_session),
) -> list[ItemResponse]:
    items = store.get_items(
        session,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )
    return [ItemMapper.to_domain(orm_item) for orm_item in items]


@router.put("/{id}")
async def update_item(
    id: int, item_request: ItemRequest, session: Session = Depends(get_session)
) -> ItemResponse:
    orm_item = store.update_item(
        session, id, item_request.name, item_request.price, item_request.deleted
    )
    if not orm_item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_MODIFIED,
            detail=f"Item with id={id} not found",
        )
    return ItemMapper.to_domain(orm_item)


@router.patch("/{id}")
async def patch_item(
    id: int, patch_request: PatchItemRequest, session: Session = Depends(get_session)
) -> ItemResponse:
    orm_item = store.patch_item(session, id, patch_request.name, patch_request.price)
    if not orm_item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_MODIFIED,
            detail=f"Item with id={id} not found or deleted",
        )
    return ItemMapper.to_domain(orm_item)


@router.delete("/{id}")
async def delete_item(id: int, session: Session = Depends(get_session)) -> Response:
    store.delete_item(session, id)
    return Response(status_code=HTTPStatus.OK)
