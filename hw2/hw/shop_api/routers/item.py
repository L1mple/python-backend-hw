from http import HTTPStatus
from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import NonNegativeInt, PositiveInt

from shop_api import data_storage
from shop_api.schemas import ItemRequest, ItemResponse, PatchItemRequest


router = APIRouter(
    prefix="/item",
    tags=["item"],
)

@router.post("/", response_model=ItemResponse)
async def create_item(item: ItemRequest):
    created_item = data_storage.create_item(item.name, item.price)

    return JSONResponse(
        created_item, 
        status_code=HTTPStatus.CREATED
        )

@router.get("/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int):
    item = data_storage.get_item(item_id)
    
    if item is None or item["deleted"]:
        return Response("Item with specified id does not exists or deleted!", status_code=HTTPStatus.NOT_FOUND)
    
    return JSONResponse(item, status_code=HTTPStatus.OK)


@router.get("/")
async def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: int | None = None,
    max_price: int | None = None,
    show_deleted: bool = False):
    items: list = data_storage.get_items()
    
    if min_price is not None and min_price < 0:
        return Response("MinPrice must be not negative!", status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    if max_price is not None and max_price < 0:
        return Response("MaxPrice must be not negative!", status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    
    if min_price is None:
        min_price = 0
    
    if max_price is None:
        max_price = float("inf") # type: ignore
    
    items = list(filter(lambda x: (not x["deleted"] if not show_deleted else True) and x["price"] >= min_price and x["price"] <= max_price, items))
    
    items = items[offset: offset + limit]
    
    return JSONResponse(items, status_code=HTTPStatus.OK)


@router.put("/{item_id}")
async def update_item(item_id: int, item_params: ItemRequest):
    item = data_storage.get_item(item_id=item_id)
    
    if item is None:
        return HTTPException(HTTPStatus.NOT_FOUND, "Item with specified id does not exists!")

    item["name"] = item_params.name
    item["price"] = item_params.price
    
    data_storage.update_item(item)
    return JSONResponse(item, status_code=HTTPStatus.OK)
    

@router.patch("/{item_id}")
async def patch_item(item_id: int, item_params: PatchItemRequest):
    item = data_storage.get_item(item_id=item_id)
    
    if item is None:
        return HTTPException(HTTPStatus.NOT_FOUND, "Item with specified id does not exists!")
    
    if item["deleted"]:
        return Response("Cannot patch deleted item!", status_code=HTTPStatus.NOT_MODIFIED)
    
    if item_params.name is not None:
        item["name"] = item_params.name
    
    if item_params.price is not None:
        item["price"] = item_params.price
            
    data_storage.update_item(item)
    
    return JSONResponse(item, status_code=HTTPStatus.OK)

@router.delete("/{item_id}")
async def delete_item(item_id: int):
    item = data_storage.get_item(item_id)
    
    if item is None:
        return HTTPException(HTTPStatus.NOT_FOUND, "Item with specified id does not exists!")

    item["deleted"] = True
    data_storage.update_item(item)
    
    return Response("Item was deleted", HTTPStatus.OK)