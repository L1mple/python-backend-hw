from http import HTTPStatus
from typing import Annotated, List
import uuid

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveFloat, PositiveInt

from shop_api.models.cart import CartOutSchema
from shop_api import local_data


router = APIRouter(prefix="/cart")


@router.post(
        "",
        response_model=CartOutSchema,
        status_code=HTTPStatus.CREATED
)
async def add_cart(response: Response):
    cart_id = str(uuid.uuid4())
    cart_data = {"id": cart_id}
    
    local_data.add_single_cart(cart_data=cart_data)

    response.headers["Location"] = f"/cart/{cart_id}"

    return cart_data


@router.get(
    "/{cart_id}",
    response_model=CartOutSchema,
    status_code=HTTPStatus.OK
)
async def get_cart_by_id(cart_id: str):
    cart_data = local_data.get_single_cart(cart_id=cart_id)

    return cart_data


@router.get(
        "",
        response_model=List[CartOutSchema],
        status_code=HTTPStatus.OK
)
async def get_all_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] = None,
    max_price: Annotated[NonNegativeFloat, Query()] = None,
    min_quantity: Annotated[NonNegativeInt, Query()] = None,
    max_quantity: Annotated[NonNegativeInt, Query()] = None,
):
    all_carts = local_data.get_all_carts()

    filtered_carts: List[CartOutSchema] = []
    for cart in all_carts:
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
        if min_quantity is not None and sum([item.quantity for item in cart.items]) < min_quantity:
            continue
        if max_quantity is not None and sum([item.quantity for item in cart.items]) > max_quantity:
            continue

        filtered_carts.append(cart)
    
    filtered_carts = filtered_carts[offset: offset + limit]

    return filtered_carts


@router.post(
        "/{cart_id}/add/{item_id}",
        response_model=CartOutSchema,
        status_code=HTTPStatus.OK
)
async def add_item_to_cart(
    cart_id: str,
    item_id: str
):
    cart = local_data.get_single_cart(cart_id=cart_id)

    if cart is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with {cart_id=!r} wasn't found",
        )
    
    item_ids = local_data.get_all_item_ids_for_cart(
        cart_id=cart_id
    )

    if item_id in item_ids:
        for item in cart.items:
            if item_id == item.id:
                item.quantity += 1
    else:
        cart.items.append(
            local_data.get_single_item(
                item_id=item_id
            )
        )
    
    return cart
