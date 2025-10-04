from fastapi import APIRouter, status, Response, Query
from fastapi.responses import JSONResponse
from http import HTTPStatus
from typing import List, Optional

from store.queries.item import (
    add_item, get_item_by_id,
    list_items, update_item_full,
    update_item_partial, delete_item,
    data_item
)
from shop_api.schemas import (
    ItemCreate,
    ItemResponse,
    CartResponse,
    Msg
)




router = APIRouter(
    prefix="/item",
    tags=["Item"]
)


@router.post(
    path="",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_item_endpoint(item: ItemCreate):
    if not item.price or not item.name:
        return JSONResponse(
            content=Msg(
                msg="Не заполнены нужные поля"
            ).model_dump(),
            status_code=422
        )
    new_item = add_item(
        name=item.name,
        price=item.price,
    )
    return new_item


@router.get(
    path="/{id}",
    response_model=ItemResponse
)
async def get_item_endpoint(id: int):
    item = get_item_by_id(id)
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
        show_deleted: Optional[bool] = Query(False)
):
    items = list_items(
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
        id: int,
        item: ItemCreate
):

    if not item.price or not item.name:
        return JSONResponse(
            content=Msg(
                msg="Отсутствуют некоторые параметры"
            ).model_dump(),
            status_code=422

        )
    if id not in data_item:
        return JSONResponse(
            content=Msg(
                msg="Ничего не найдено"
            ).model_dump(),
            status_code=404
        )

    item = update_item_full(
        item_id=id,
        name=item.name,
        price=item.price
    )

    return item


@router.patch(
    path="/{id}",
    response_model=ItemResponse
)
async def update_item_partial_endpoint(
        id: int,
        item: ItemCreate
):

    if id not in data_item:
        return JSONResponse(
            content=Msg(
                msg="Ничего не найдено"
            ).model_dump(),
            status_code=404
        )

    if data_item[id].deleted:
        return JSONResponse(
            content=Msg(
                msg="Айтем удален"
            ).model_dump(),
            status_code=304
        )

    item = update_item_partial(
        item_id=id,
        name=item.name,
        price=item.price,
    )

    return item


@router.delete(
    path="/{id}",
    response_model=ItemResponse
)
async def delete_item_endpoint(id: int):
    item = delete_item(id)

    if not item:
        return JSONResponse(
            content=Msg(
                msg="Ничего не найдено"
            ).model_dump(),
            status_code=HTTPStatus.NOT_FOUND
        )

    return item