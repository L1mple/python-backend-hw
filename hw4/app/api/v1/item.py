from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

import app.crud.item as crud_item
from app.core.mongo import get_mongo
from app.schemas.item import CreateItem, PatchItem, UpdateItem

# Роутер товаров
router = APIRouter(tags=["item"])


@router.post("/item")
async def create_item(item: CreateItem, mongo=Depends(get_mongo)):
    item = await crud_item.create_item(mongo, item)
    return JSONResponse(
        content=item.model_dump(),
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/item/{item.id}"},
    )


@router.get("/item/{item_id}")
async def get_item_by_id(item_id: int, mongo=Depends(get_mongo)):
    item = await crud_item.get_item_by_id(mongo, item_id)
    if item is None:
        return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
    else:
        return JSONResponse(content=item.model_dump(), status_code=status.HTTP_200_OK)


@router.put("/item/{item_id}")
async def update_item(item_id: int, item: UpdateItem, mongo=Depends(get_mongo)):
    item = await crud_item.update_item(mongo, item_id, item)
    if item is None:
        return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
    else:
        return JSONResponse(content=item.model_dump(), status_code=status.HTTP_200_OK)


@router.patch("/item/{item_id}")
async def patch_item(item_id: int, item: PatchItem, mongo=Depends(get_mongo)):
    item, code = await crud_item.patch_item(mongo, item_id, item)
    if code == 404:
        return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
    if code == 304:
        return JSONResponse(content={}, status_code=status.HTTP_304_NOT_MODIFIED)
    return JSONResponse(content=item.model_dump(), status_code=status.HTTP_200_OK)


@router.delete("/item/{item_id}")
async def delete_item(item_id: int, mongo=Depends(get_mongo)):
    item = await crud_item.delete_item(mongo, item_id)
    if item is None:
        return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
    else:
        return JSONResponse(content=item.model_dump(), status_code=status.HTTP_200_OK)


@router.get("/item")
async def get_items(
    offset: int = 0,
    limit: int = 10,
    min_price: float = None,
    max_price: float = None,
    show_deleted: bool = False,
    mongo=Depends(get_mongo),
):
    items, code = await crud_item.get_items(mongo, offset, limit, min_price, max_price, show_deleted)
    if code == 422:
        return JSONResponse(content=[], status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    return JSONResponse(content=[item.model_dump() for item in items], status_code=status.HTTP_200_OK)
