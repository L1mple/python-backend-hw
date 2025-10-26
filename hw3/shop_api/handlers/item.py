from http import HTTPStatus
from typing import Annotated, List
import uuid

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt

from shop_api.models.cart import CartOutSchema
from shop_api import local_data
from shop_api.models.item import ItemPatchSchema, ItemSchema, ItemCreateSchema


router = APIRouter(prefix="/item")


@router.post(
        "",
        response_model=ItemSchema,
        status_code=HTTPStatus.CREATED,
)
async def add_item(
        response: Response,
        item: ItemCreateSchema
):
    item_id = str(uuid.uuid4())
    item_data = {
        "id": item_id,
        **item.model_dump()
    }
    
    local_data.add_single_item(
        item_id=item_id,
        item_data=item_data
    )

    response.headers["Location"] = f"/item/{item_id}"

    return item_data


@router.get(
    "/{item_id}",
    response_model=ItemSchema,
    status_code=HTTPStatus.OK
)
async def get_item_by_id(item_id: str):
    item_data = local_data.get_single_item(item_id=item_id)
    if item_data.deleted:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with {item_id=!r} was deleted"
        )
    return item_data


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
):
    all_items = local_data.get_all_items()

    filtered_items: List[ItemSchema] = []
    for item in all_items:
        if min_price and item.price < min_price:
            continue
        if max_price and item.price > max_price:
            continue
        if not show_deleted and item.deleted:
            continue

        filtered_items.append(item)
    
    filtered_items = filtered_items[offset: offset + limit]

    return filtered_items


@router.put(
        "/{item_id}",
        response_model=ItemSchema,
        status_code=HTTPStatus.OK
)
async def change_item(
        item_id: str,
        item: ItemSchema
):
    if local_data.get_single_item(item_id=item_id) is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with {item_id=!r} is not found"
        )

    local_data.add_single_item(
        item_id=item_id, 
        item_data=item
    )

    return item


@router.patch(
    "/{item_id}",
    response_model=ItemSchema,
    status_code=HTTPStatus.OK
)
async def change_item_fields(
    item_id: str,
    item: ItemPatchSchema
):
    old_item = local_data.get_single_item(item_id=item_id)
    if old_item is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with {item_id=!r} is not found"
        )
    
    if old_item.deleted:
        raise HTTPException(
            HTTPStatus.NOT_MODIFIED,
            f"Item with {item_id=!r} has been deleted"
        )
    
    update_data = item.model_dump(exclude_unset=True)
    updated_item = old_item.model_copy(update=update_data)
    
    local_data.add_single_item(
        item_id=item_id,
        item_data=updated_item
    )

    return updated_item


@router.delete(
        "/{item_id}",
        response_model=ItemSchema,
        status_code=HTTPStatus.OK
)
async def delete_item(item_id: str):
    item_data = local_data.get_single_item(item_id=item_id)
    if item_data is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with {item_id=!r} is not found"
        )

    local_data.delete_item(item_id=item_id)
    return item_data
    