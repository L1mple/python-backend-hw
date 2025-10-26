from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, HTTPException, status
from pydantic import NonNegativeInt, PositiveInt

from sqlalchemy.orm import Session

from shop_api.store.database import get_session
from shop_api.store.queries import (
    add_cart_item,
    create_cart_record,
    get_cart as get_cart_record,
    get_item,
    list_carts,
)
from shop_api.store.models import Cart


router = APIRouter(prefix="/cart")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_cart(
    response: Response,
    session: Session = Depends(get_session),
) -> Cart:
    cart = create_cart_record(session)
    response.headers["Location"] = f"/cart/{cart.id}"
    return cart


@router.get("/")
async def get_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(gt=0)] = None,
    max_price: Annotated[float | None, Query(gt=0)] = None,
    min_quantity: Annotated[int | None, Query(gt=0)] = None,
    max_quantity: Annotated[int | None, Query(ge=0)] = None,
    session: Session = Depends(get_session),
) -> list[Cart]:
    return list_carts(
        session,
        offset,
        limit,
        min_price,
        max_price,
        min_quantity,
        max_quantity,
    )


@router.get("/{id}")
async def get_cart(id: int, session: Session = Depends(get_session)) -> Cart:
    cart = get_cart_record(session, id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return cart


@router.post("/{cart_id}/add/{item_id}", status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(
    cart_id: int,
    item_id: int,
    session: Session = Depends(get_session),
) -> Cart:
    cart = get_cart_record(session, cart_id)
    if cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    item = get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    updated_cart = add_cart_item(session, cart_id, item_id)
    if updated_cart is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Unable to update cart")
    return updated_cart
