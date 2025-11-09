from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt


from shop_api.db import get_db
from shop_api.cart import store
from shop_api.cart.contracts import CartResponse

import shop_api
import shop_api.item
import shop_api.item.store

from sqlalchemy.orm import Session

router = APIRouter(prefix="/cart")


@router.post("/", status_code=HTTPStatus.CREATED)
async def post_cart(response: Response, db: Session = Depends(get_db)) -> CartResponse:
    entity = store.create(db)

    response.headers["location"] = f"/cart/{entity.id}"
    return CartResponse.from_entity(entity)


@router.get(
    "/{cart_id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested cart",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested cart as one was not found",
        },
    },
)
async def get_cart_by_id(cart_id: int, db: Session = Depends(get_db)):
    entity = store.get_one(db, cart_id)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{cart_id} was not found",
        )

    return CartResponse.from_entity(entity)


@router.get("/")
async def get_cart_list(
    db: Session = Depends(get_db),
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] | None = None,
    max_price: Annotated[NonNegativeFloat, Query()] | None = None,
    min_quantity: Annotated[NonNegativeFloat, Query()] | None = None,
    max_quantity: Annotated[NonNegativeFloat, Query()] | None = None,
):
    entities = store.get_many(
        db=db,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )
    return [CartResponse.from_entity(e) for e in entities]


@router.post("/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    item_entity = shop_api.item.store.get_one(db, item_id)

    entity = store.add(db, cart_id, item_entity)

    return CartResponse.from_entity(entity)
