from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from shop_api.database import get_session
from shop_api.models.item import Item
from shop_api.schemas.item import ItemCreate, ItemOut
from shop_api.metrics import items_in_stock_gauge

router = APIRouter(prefix="/item", tags=["item"])


@router.post("/", response_model=ItemOut, status_code=201)
async def create_item(item: ItemCreate, session: AsyncSession = Depends(get_session)):
    new_item = Item(**item.dict())
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)

    items_in_stock_gauge.inc()
    return new_item


@router.get("/{item_id}", response_model=ItemOut)
async def get_item(item_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(Item, item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.get("/", response_model=List[ItemOut])
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    query = select(Item)
    if not show_deleted:
        query = query.where(Item.deleted.is_(False))
    if min_price is not None:
        query = query.where(Item.price >= min_price)
    if max_price is not None:
        query = query.where(Item.price <= max_price)

    result = await session.execute(query.offset(offset).limit(limit))
    return result.scalars().all()


@router.delete("/{item_id}", status_code=200)
async def delete_item(item_id: int, session: AsyncSession = Depends(get_session)):
    item = await session.get(Item, item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not item.deleted:
        item.deleted = True
        await session.commit()
        items_in_stock_gauge.dec()
    return {"status": "ok"}
