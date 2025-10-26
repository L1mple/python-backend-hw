from http import HTTPStatus
from typing import Annotated, List
import uuid

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from shop_api.db.session import get_db


from shop_api.models.item import (
    Item as ItemModel,
    ItemSchema, 
    ItemCreateSchema, 
    ItemPatchSchema
)

router = APIRouter(prefix="/item")


@router.post(
        "",
        response_model=ItemSchema,
        status_code=HTTPStatus.CREATED,
)
async def add_item(
        response: Response,
        item: ItemCreateSchema,
        db: AsyncSession = Depends(get_db) 
):
    db_item = ItemModel(**item.model_dump())
    
    db.add(db_item)
    await db.commit()
    await db.refresh(db_item)

    response.headers["Location"] = f"/item/{db_item.id}"
    return db_item


@router.get(
    "/{item_id}",
    response_model=ItemSchema,
    status_code=HTTPStatus.OK
)
async def get_item_by_id(
    item_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Invalid item_id format")

    query = select(ItemModel).where(ItemModel.id == item_uuid)
    result = await db.execute(query)
    db_item = result.scalar_one_or_none()

    if db_item is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Item with {item_id=} is not found")
        
    if db_item.deleted:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Item with {item_id=} was deleted")
    
    return db_item


@router.get(
        "",
        response_model=List[ItemSchema],
        status_code=HTTPStatus.OK
)
async def get_all_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] = None,
    max_price: Annotated[NonNegativeFloat, Query()] = None,
    show_deleted: Annotated[bool, Query()] = False,
    db: AsyncSession = Depends(get_db)
):
    query = select(ItemModel)

    if min_price:
        query = query.where(ItemModel.price >= min_price)
    if max_price:
        query = query.where(ItemModel.price <= max_price)
    if not show_deleted:
        query = query.where(ItemModel.deleted == False)

    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    all_items = result.scalars().all()

    return all_items


@router.put(
        "/{item_id}",
        response_model=ItemSchema,
        status_code=HTTPStatus.OK
)
async def change_item(
        item_id: str,
        item: ItemSchema, 
        db: AsyncSession = Depends(get_db)
):
    db_item = await get_item_by_id(item_id, db) 

    db_item.name = item.name
    db_item.price = item.price
    db_item.deleted = item.deleted
    
    await db.commit()
    await db.refresh(db_item)

    return db_item


@router.patch(
    "/{item_id}",
    response_model=ItemSchema,
    status_code=HTTPStatus.OK
)
async def change_item_fields(
    item_id: str,
    item: ItemPatchSchema,
    db: AsyncSession = Depends(get_db)
):
    db_item = (await db.execute(
        select(ItemModel).where(ItemModel.id == uuid.UUID(item_id))
    )).scalar_one_or_none()

    if db_item is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Item with {item_id=} is not found")
    
    if db_item.deleted:
        raise HTTPException(HTTPStatus.NOT_MODIFIED, f"Item with {item_id=} has been deleted")

    update_data = item.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(db_item, key, value)

    await db.commit()
    await db.refresh(db_item)

    return db_item


@router.delete(
        "/{item_id}",
        response_model=ItemSchema,
        status_code=HTTPStatus.OK
)
async def delete_item(
    item_id: str,
    db: AsyncSession = Depends(get_db)
):
    db_item = (await db.execute(
        select(ItemModel).where(ItemModel.id == uuid.UUID(item_id))
    )).scalar_one_or_none()

    if db_item is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Item with {item_id=} is not found")

    db_item.deleted = True
    await db.commit()
    await db.refresh(db_item)

    return db_item
