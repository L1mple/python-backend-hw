from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from shop_api.store.queries import (
    add_cart,
    add_item_to_cart,
    get_cart,
    get_carts,
    get_item,
)

from .contracts import CartIdResponse, CartResponse

router = APIRouter(prefix="/cart")


@router.post(
    "",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(response: Response) -> CartIdResponse:
    entity = add_cart()
    response.headers["location"] = f"/cart/{entity.id}"
    return CartIdResponse(id=entity.id)


@router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested cart",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Cart not found",
        },
    },
)
async def get_cart_by_id(id: int) -> CartResponse:
    entity = get_cart(id)
    
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id={id} not found",
        )
    
    items_dict = {}
    for cart_item in entity.info.items:
        item_entity = get_item(cart_item.id, include_deleted=True)
        if item_entity:
            items_dict[cart_item.id] = item_entity
    
    return CartResponse.from_entity(entity, items_dict)


@router.get("")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None,
) -> list[CartResponse]:
    entities = get_carts(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )
    
    all_item_ids = set()
    for cart_entity in entities:
        for cart_item in cart_entity.info.items:
            all_item_ids.add(cart_item.id)
    
    items_dict = {}
    for item_id in all_item_ids:
        item_entity = get_item(item_id, include_deleted=True)
        if item_entity:
            items_dict[item_id] = item_entity
    
    return [CartResponse.from_entity(e, items_dict) for e in entities]


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
async def add_item_to_cart_handler(cart_id: int, item_id: int) -> CartResponse:
    entity = add_item_to_cart(cart_id, item_id)
    
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id={cart_id} or item with id={item_id} not found",
        )
    
    items_dict = {}
    for cart_item in entity.info.items:
        item_entity = get_item(cart_item.id, include_deleted=True)
        if item_entity:
            items_dict[cart_item.id] = item_entity
    
    return CartResponse.from_entity(entity, items_dict)
