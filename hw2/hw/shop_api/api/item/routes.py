from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from pydantic import NonNegativeInt, PositiveInt

from sqlalchemy.orm import Session

from shop_api.store.database import get_session
from shop_api.store.queries import (
    create_item_record,
    delete_item,
    get_item as get_item_record,
    list_items,
    patch_item_record,
    replace_item_record,
)
from shop_api.store.models import Item
from shop_api.api.item.contracts import ItemPostRequest, ItemPutRequest, ItemPatchRequest


router = APIRouter(prefix="/item")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_item(
    request: ItemPostRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> Item:
    item = create_item_record(session, request.name, request.price)
    response.headers["Location"] = f"/item/{item.id}"
    return item


@router.get("/")
async def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(gt=0)] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    show_deleted: Annotated[bool, Query()] = False,
    session: Session = Depends(get_session),
) -> list[Item]:
    return list_items(
        session,
        offset,
        limit,
        min_price,
        max_price,
        show_deleted,
    )


@router.get("/{id}")
async def get_item(id: int, session: Session = Depends(get_session)) -> Item:
    item = get_item_record(session, id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return item


@router.put("/{id}")
async def put_item(
    id: int,
    request: ItemPutRequest,
    session: Session = Depends(get_session),
) -> Item:
    updated = replace_item_record(session, id, request.name, request.price)
    if updated is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return updated


@router.patch("/{id}")
async def patch_item(
    id: int,
    request: ItemPatchRequest,
    session: Session = Depends(get_session),
) -> Item:
    patched = patch_item_record(session, id, request.name, request.price)
    if patched is None:
        raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED)
    return patched


@router.delete("/{id}")
async def delete_item_route(
    id: int,
    session: Session = Depends(get_session),
) -> None:
    delete_item(session, id)
