from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt
from sqlalchemy.orm import Session

from . import store
from .contracts import CartIdResponse, CartMapper, CartResponse
from .database import get_session

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("/", status_code=HTTPStatus.CREATED)
@router.post("", status_code=HTTPStatus.CREATED)
async def create_cart(
    response: Response, session: Session = Depends(get_session)
) -> CartIdResponse:
    cart = store.add_cart(session)
    response.headers["location"] = f"/cart/{cart.id}"
    return CartIdResponse(id=cart.id)


@router.get("/{id}")
async def get_cart_by_id(
    id: int, session: Session = Depends(get_session)
) -> CartResponse:
    orm_cart = store.get_cart(session, id)
    if not orm_cart:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Cart with id={id} not found",
        )
    return CartMapper.to_domain(orm_cart)


@router.get("/")
@router.get("")
async def get_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    session: Session = Depends(get_session),
) -> list[CartResponse]:
    carts = store.get_carts(
        session,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )
    return [CartMapper.to_domain(orm_cart) for orm_cart in carts]


@router.post("/{cart_id}/add/{item_id}")
async def add_item_to_cart(
    cart_id: int, item_id: int, session: Session = Depends(get_session)
) -> CartResponse:
    orm_cart = store.get_cart(session, cart_id)
    if not orm_cart:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Cart with id={cart_id} not found",
        )
    orm_item = store.get_item(session, item_id)
    if not orm_item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Item with id={item_id} not found",
        )
    ret_cart = store.add_item_to_cart(session, orm_cart, orm_item)
    return CartMapper.to_domain(ret_cart)
