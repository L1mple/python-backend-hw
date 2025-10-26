from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, Request, Depends
from sqlalchemy.orm import Session
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat

from shop_api import store
from shop_api.database import get_db

from shop_api.api.cart.contracts import CartResponse

router = APIRouter(prefix="/cart")


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(_: Request, response: Response, db: Session = Depends(get_db)) -> CartResponse:
    entity = store.add_cart(db)

    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/cart/{entity.id}"

    return CartResponse.from_orm(entity)


@router.get(
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
async def get_cart_by_id(id: int, db: Session = Depends(get_db)) -> CartResponse:
    entity = store.get_one_cart(db, id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{id} was not found",
        )

    return CartResponse.from_orm(entity)


@router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] = 0,
    max_price: Annotated[NonNegativeFloat, Query()] = 1e10,
    min_quantity: Annotated[NonNegativeInt, Query()] = 0,
    max_quantity: Annotated[NonNegativeInt, Query()] = 1e10,
    db: Session = Depends(get_db)
) -> list[CartResponse]:
    return [CartResponse.from_orm(e) for e in store.get_many_carts(db, offset, limit, min_price, max_price, min_quantity, max_quantity)]


@router.post(
    "/{cart_id}/add/{item_id}",
    status_code=HTTPStatus.CREATED,
)
async def post_item_to_cart(cart_id: int, item_id: int, response: Response, db: Session = Depends(get_db)) -> CartResponse:
    entity = store.add_item_to_cart(db, cart_id, item_id)

    response.headers["location"] = f"/cart/{entity.id}"

    return CartResponse.from_orm(entity)
