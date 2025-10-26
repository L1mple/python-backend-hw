from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from decimal import Decimal

from .store import create, get_list, get_one, add_item_to_cart
from .contracts import CartResponse, CartInfo
from ...database.schemas import UserCreate, ProductCreate
from ...database import get_db
from ...database.models import User, Product

router = APIRouter(prefix="/cart")


def _get_entity_or_404(entity, resource_path: str):
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource {resource_path} was not found",
        )
    return entity


@router.get("/")
async def get_cart_list(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1)] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    min_quantity: Annotated[int | None, Query(ge=0)] = None,
    max_quantity: Annotated[int | None, Query(ge=0)] = None,
) -> list[CartResponse]:
    return [CartResponse.from_entity(e) for e in get_list(offset, limit, min_price, max_price, min_quantity, max_quantity)]


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
async def get_cart_by_id(id: int) -> CartResponse:
    entity = _get_entity_or_404(get_one(id), f"/cart/{id}")
    return CartResponse.from_entity(entity)


@router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(response: Response) -> CartResponse:
    cart_info = CartInfo(items=[], price=Decimal('0'))
    entity = create(cart_info)

    response.headers["location"] = f"/cart/{entity.id}"

    return CartResponse.from_entity(entity)


@router.post(
    "/{cart_id}/add/{item_id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully added item to cart",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to add item to cart as one was not found",
        },
    },
)
async def add_item(cart_id: int, item_id: int) -> CartResponse:
    entity = _get_entity_or_404(add_item_to_cart(cart_id, item_id), f"/cart/{cart_id}")
    return CartResponse.from_entity(entity)
