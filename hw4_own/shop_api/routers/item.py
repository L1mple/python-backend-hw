from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import Select, and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from shop_api.core.schemas import ItemOut, ItemCreate, ItemPut, ItemPatch
from shop_api.core.db import get_session
from shop_api.core.models import Item
from shop_api.core import storage as crud

router = APIRouter(prefix="/item", tags=["items"])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ItemOut)
async def create_item(body: ItemCreate, session: AsyncSession = Depends(get_session)) -> ItemOut:
    obj = await crud.create_item(session, body)
    await session.commit()
    return obj


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(item_id: int, session: AsyncSession = Depends(get_session)) -> ItemOut:
    item = await crud.get_item_or_404(session, item_id)
    return ItemOut(id=item.id, name=item.name, price=item.price, deleted=item.deleted)


@router.get("", response_model=List[ItemOut])
async def list_items(
    offset: int = Query(0, ge=0, description="Смещение (offset)"),
    limit: int = Query(10, gt=0, description="Количество (limit)"),
    min_price: Optional[float] = Query(None, ge=0, description="Мин. цена"),
    max_price: Optional[float] = Query(None, ge=0, description="Макс. цена"),
    show_deleted: bool = Query(False, description="Показывать ли удалённые"),
    session: AsyncSession = Depends(get_session),
) -> List[ItemOut]:
    stmt: Select = select(Item)
    conds = []
    if not show_deleted:
        conds.append(Item.deleted.is_(False))
    if min_price is not None:
        conds.append(Item.price >= min_price)
    if max_price is not None:
        conds.append(Item.price <= max_price)
    if conds:
        stmt = stmt.where(and_(*conds))
    stmt = stmt.offset(offset).limit(limit)

    res = await session.execute(stmt)
    items = res.scalars().all()
    return [ItemOut(id=i.id, name=i.name, price=i.price, deleted=i.deleted) for i in items]


@router.put("/{item_id}", response_model=ItemOut)
async def put_item(item_id: int, body: ItemPut, session: AsyncSession = Depends(get_session)) -> ItemOut:
    obj = await crud.put_item(session, item_id, body)
    await session.commit()
    return obj


@router.patch("/{item_id}", response_model=ItemOut)
async def patch_item(item_id: int, body: ItemPatch, session: AsyncSession = Depends(get_session)):
    try:
        obj = await crud.patch_item(session, item_id, body)
    except HTTPException as e:
        if e.status_code == status.HTTP_304_NOT_MODIFIED:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED)
        raise
    await session.commit()
    return obj


@router.delete("/{item_id}")
async def delete_item(item_id: int, session: AsyncSession = Depends(get_session)):
    result = await crud.delete_item(session, item_id)
    await session.commit()
    return result
