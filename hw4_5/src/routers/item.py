from uuid import UUID
from fastapi import APIRouter, status, Query, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud import crud_item
from src.db import get_db
from src.schemas import (
    ItemCreate,
    ItemResponse,
    Msg, ItemUpdate, ItemPatch
)

router = APIRouter()


@router.post(
    path="",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_item_endpoint(
    item: ItemCreate,
    db: AsyncSession = Depends(get_db)
):
    new_item = await crud_item.create(db=db, obj_in=item)
    return new_item


@router.get(
    path="/{id}",
    response_model=ItemResponse
)
async def get_item_endpoint(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    item = await crud_item.get(db=db, id=id)
    if not item:
        return JSONResponse(
            content=Msg(
                msg="Ничего не найдено"
            ).model_dump(),
            status_code=404
        )
    return item


@router.get(
    path="",
    response_model=List[ItemResponse]
)
async def get_list_items_endpoint(
        offset: Optional[int] = Query(None, ge=0),
        limit: Optional[int] = Query(None, ge=1),
        min_price: Optional[float] = Query(None, ge=0.0),
        max_price: Optional[float] = Query(None, ge=0.0),
        show_deleted: Optional[bool] = Query(False),
        db: AsyncSession = Depends(get_db)
):
    items = await crud_item.get_items_with_filters(
        db=db,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted
    )

    return items


@router.put(
    path="/{id}",
    response_model=ItemResponse
)
async def update_full_item_endpoint(
    id: UUID,
    item: ItemUpdate,
    db: AsyncSession = Depends(get_db)
):

    item_updated = await crud_item.update(
        db=db,
        id=id,
        obj_in=item
    )
    if not item_updated:
        return JSONResponse(
            content=Msg(
                msg="Ничего не найдено"
            ).model_dump(),
            status_code=404
        )

    return item_updated


@router.patch(
    path="/{id}",
    response_model=ItemResponse
)
async def update_item_partial_endpoint(
    id: UUID,
    item: ItemPatch,
    db: AsyncSession = Depends(get_db)
):

    item_patched = await crud_item.update(
        db=db,
        id=id,
        obj_in=item
    )

    if not item_patched:
        return JSONResponse(
            content=Msg(
                msg="Ничего не найдено"
            ).model_dump(),
            status_code=404
        )

    return item_patched


@router.delete(
    path="/{id}",
    response_model=ItemResponse
)
async def delete_item_endpoint(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    item_deleted = await crud_item.soft_delete(
        db=db,
        id=id
    )

    if not item_deleted:
        return JSONResponse(
            content=Msg(
                msg="Ничего не найдено"
            ).model_dump(),
            status_code=404
        )
    return item_deleted