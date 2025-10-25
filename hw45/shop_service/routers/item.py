from http import HTTPStatus
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Response, Depends
from pydantic import NonNegativeInt, PositiveInt

from sqlalchemy.orm import Session

from db.utils import get_db
from db.item import ItemService, SqlAlchemyItemRepository
from shop_service.schemas import ItemRequest, ItemResponse, PatchItemRequest


router = APIRouter(
    prefix="/item",
    tags=["item"],
)

@router.post("/", response_model=ItemResponse, status_code=HTTPStatus.CREATED)
async def create_item(item: ItemRequest, db: Session = Depends(get_db)):
    item_service = ItemService(SqlAlchemyItemRepository(db))
    created_item = item_service.create_item(item.name, item.price)
    return created_item

@router.get("/{item_id}", response_model=ItemResponse, status_code=HTTPStatus.OK)
async def get_item(item_id: int, db: Session = Depends(get_db)):
    item_service = ItemService(SqlAlchemyItemRepository(db))
    item = item_service.get_item(item_id)
    
    if item is None or item.deleted:
        return Response("Item with specified id does not exists or deleted!", status_code=HTTPStatus.NOT_FOUND)
    
    return item


@router.get("/", status_code=HTTPStatus.OK)
async def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeInt, Query()] | None = None,
    max_price: Annotated[NonNegativeInt, Query()] | None = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db)
    ):
    item_service = ItemService(SqlAlchemyItemRepository(db))
    items: list = item_service.get_items()

    if min_price is None:
        min_price = 0
    
    if max_price is None:
        max_price = float("inf") # type: ignore
    
    items = list(filter(lambda x: (not x.deleted if not show_deleted else True) and x.price >= min_price and x.price <= max_price, items))
    
    items = items[offset: offset + limit]
    
    return items


@router.put("/{item_id}", status_code=HTTPStatus.OK)
async def update_item(item_id: int, item_params: ItemRequest, db: Session = Depends(get_db)):
    item_service = ItemService(SqlAlchemyItemRepository(db))
    
    item = item_service.get_item(item_id=item_id)
    
    if item is None:
        return Response("Item with specified id does not exists!", status_code=HTTPStatus.NOT_FOUND)

    item.name = item_params.name
    item.price = item_params.price
    
    item_service.update_item(item)
    return item
    

@router.patch("/{item_id}")
async def patch_item(item_id: int, item_params: PatchItemRequest, db: Session = Depends(get_db)):
    item_service = ItemService(SqlAlchemyItemRepository(db))
    item = item_service.get_item(item_id=item_id)
    
    if item is None:
        return Response("Item with specified id does not exists!", status_code=HTTPStatus.NOT_FOUND)
    
    if item.deleted:
        return Response("Cannot patch deleted item!", status_code=HTTPStatus.NOT_MODIFIED)
    
    if item_params.name is not None:
        item.name = item_params.name
    
    if item_params.price is not None:
        item.price = item_params.price
            
    item_service.update_item(item)
    
    return item

@router.delete("/{item_id}", status_code=HTTPStatus.OK)
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    item_service = ItemService(SqlAlchemyItemRepository(db))
    
    try:
        item_service.delete_item(item_id=item_id)
    except ValueError:
        return HTTPException(HTTPStatus.NOT_FOUND, "Item with specified id does not exists!")
    
    return Response("Item was deleted")