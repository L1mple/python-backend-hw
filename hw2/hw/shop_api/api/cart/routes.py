from http import HTTPStatus
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat
from sqlalchemy.orm import Session

from shop_api import store

from .contracts import (
    CartResponse,
    CartMapper
)

cart_router = APIRouter(prefix="/cart")


@cart_router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    db: Session = Depends(store.get_db)
) -> list[CartResponse]:
    return [CartMapper.to_domain(orm_cart) for orm_cart in store.get_carts(db, offset, limit, min_price, max_price, min_quantity, max_quantity)]


@cart_router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested cart",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested cart as one was not found",
        },
    },
)
async def get_cart_by_id(id: int, db: Session = Depends(store.get_db)) -> CartResponse:
    orm_cart = store.get_cart(db, id)

    if not orm_cart:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{id} was not found",
        )
    
    return CartMapper.to_domain(orm_cart)


@cart_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(response: Response, db: Session = Depends(store.get_db)) -> CartResponse:
    orm_cart = store.add_cart(db)

    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/cart/{orm_cart.id}"

    return CartMapper.to_domain(orm_cart)


@cart_router.post(
    "/{cart_id}/add/{item_id}",
    status_code=HTTPStatus.CREATED,
)
async def post_cart_item(cart_id: int, item_id: int, db: Session = Depends(store.get_db)) -> CartResponse:
    orm_cart = store.get_cart(db, cart_id)

    if not orm_cart:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{cart_id} was not found",
        )
    

    orm_item = store.get_item(db, item_id)

    if not orm_item:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /item/{item_id} was not found",
        )
 
    ret_orm_cart = store.add_item_to_cart(db, orm_cart, orm_item)

    return CartMapper.to_domain(ret_orm_cart)
