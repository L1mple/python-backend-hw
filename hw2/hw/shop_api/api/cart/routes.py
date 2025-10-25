from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt

from shop_api.store.dependencies import get_cart_service
from shop_api.store.services import CartService

from .contracts import CartResponse, CartIdResponse

router = APIRouter(prefix="/cart")


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(
    response: Response,
    service: CartService = Depends(get_cart_service),
) -> CartIdResponse:
    """Create a new empty cart (RPC-style endpoint)"""
    entity = service.create_cart()
    response.headers["location"] = f"/cart/{entity.id}"
    return CartIdResponse.from_entity(entity)


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
async def get_cart_by_id(
    id: int,
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    """Get cart by ID"""
    try:
        entity = service.get_cart(id)
        return CartResponse.from_entity(entity)
    except ValueError as e:
        raise HTTPException(HTTPStatus.NOT_FOUND, str(e))


@router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    service: CartService = Depends(get_cart_service),
) -> list[CartResponse]:
    """Get list of carts with optional filtering"""
    # List operations can go through repository (no business logic needed)
    entities = service.cart_repo.find_many(
        offset, limit, min_price, max_price, min_quantity, max_quantity
    )
    return [CartResponse.from_entity(e) for e in entities]


@router.post(
    "/{cart_id}/add/{item_id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully added item to cart",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Cart or item not found",
        },
    },
)
async def add_item_to_cart(
    cart_id: int,
    item_id: int,
    service: CartService = Depends(get_cart_service),
) -> CartResponse:
    """Add item to cart (or increment quantity if already exists)"""
    try:
        updated_cart, _ = service.add_item_to_cart(cart_id, item_id)
        return CartResponse.from_entity(updated_cart)
    except ValueError as e:
        raise HTTPException(HTTPStatus.NOT_FOUND, str(e))
