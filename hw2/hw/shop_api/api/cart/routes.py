from typing import Annotated

from fastapi import APIRouter, Query, Response, HTTPException, status
from pydantic import NonNegativeInt, PositiveInt

from store.queries import add_cart_item, create_cart_record, list_carts, list_items
from store.models import Cart


router = APIRouter(prefix="/cart")


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response) -> Cart:
    cart = create_cart_record()
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
) -> list[Cart]:
    return list_carts(
        offset, limit, min_price, max_price, min_quantity, max_quantity
    )


@router.get("/{id}")
async def get_cart(id: int) -> Cart:
    carts = list_carts(offset=id, limit=1)
    if not carts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return carts[0]


@router.post("/{cart_id}/add/{item_id}", status_code=status.HTTP_201_CREATED)
async def add_item_to_cart(cart_id: int, item_id: int) -> Cart:
    cart = list_carts(offset=cart_id, limit=1)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    item = list_items(offset=item_id, limit=1)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    add_cart_item(cart[0], item[0])
    return cart[0]
