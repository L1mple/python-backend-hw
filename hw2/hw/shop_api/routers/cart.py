from fastapi import APIRouter, status, Response, Query
from fastapi.responses import JSONResponse
from typing import List, Optional

from store.queries.cart import (
    add_cart, get_cart_by_id,
    list_carts, add_item_to_cart
)
from shop_api.schemas import (
    CartResponse,
    CartCreateResponse,
    Msg
)




router = APIRouter(
    prefix="/cart",
    tags=["Cart"]
)


@router.post(
    path="",
    response_model=CartCreateResponse,
    status_code=status.HTTP_201_CREATED
)
def create_cart(response: Response):
    cart_id = add_cart()
    response.headers["Location"] = f"/cart/{cart_id}"
    return CartCreateResponse(id=cart_id)


@router.get(
    path="/{id}",
    response_model=CartResponse
)
async def get_cart(id: int):
    cart = get_cart_by_id(id)
    print(cart)
    if cart is None:
        return JSONResponse(
            content=Msg(msg="Корзина не найдена").model_dump(),
            status_code=404
        )

    return cart


@router.get(
    path="",
    response_model=List[CartResponse]
)
async def get_list_carts(
        offset: Optional[int] = Query(None, ge=0),
        limit: Optional[int] = Query(None, ge=1),
        min_price: Optional[float] = Query(None, ge=0.0),
        max_price: Optional[float] = Query(None, ge=0.0),
        min_quantity: Optional[int] = Query(None, ge=0),
        max_quantity: Optional[int] = Query(None, ge=0)
):

    carts = list_carts(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity
    )

    return carts


@router.post(
    path="/{cart_id}/add/{item_id}",
    response_model=CartResponse
)
async def add_item_to_cart_endpoint(
        cart_id: int,
        item_id: int
):
    cart = add_item_to_cart(
        cart_id=cart_id,
        item_id=item_id
    )

    if not cart:
        return JSONResponse(
            content=Msg(msg="Ничего не найдено").model_dump(),
            status_code=404
        )
    print(cart)
    return cart