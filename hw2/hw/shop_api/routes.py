from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from models import BaseItem, Cart, CartFilters, Item, ItemFilters, PatchItem
from queries import (add_item, add_to_cart, create_empty_cart,
                     delete_item_by_id, get_cart_by_id, get_carts_filtered,
                     get_item_by_id, get_items_filtered, patch_item_query,
                     put_item_query)

router = APIRouter()


@router.post("/cart")
async def create_cart():
    cart = create_empty_cart()
    return JSONResponse(content={"id": cart.id}, status_code=HTTPStatus.CREATED,
                        headers={"location": f"/cart/{cart.id}"})


@router.get("/cart/{cart_id}")
async def get_cart(cart_id: int) -> Cart:
    cart = get_cart_by_id(cart_id)
    if cart is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id={cart_id} was not found",
        )
    return cart


@router.post("/item", status_code=HTTPStatus.CREATED)
async def create_item(item: BaseItem, response: Response) -> Item:
    _item = add_item(item)
    response.headers["location"] = f"/item/{_item.id}"
    return _item


@router.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int) -> Cart:
    cart = add_to_cart(cart_id, item_id)
    if cart is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Could not add item to cart; either item or cart not found",
        )
    return cart


@router.get("/item/{item_id}")
async def get_item(item_id: int) -> Item:
    item = get_item_by_id(item_id)
    if item is None or item.deleted:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={item_id} was not found",
        )
    return item


@router.get("/cart")
async def get_carts_with_filters(filter_params: CartFilters = Depends()) -> list[Cart]:
    carts = get_carts_filtered(filter_params)
    return carts


@router.get("/item")
async def get_items_with_filters(filter_params: ItemFilters = Depends()) -> list[Item]:
    items = get_items_filtered(filter_params)
    return items


@router.delete("/item/{item_id}")
async def delete_item(item_id: int) -> Item:
    item = delete_item_by_id(item_id)
    if item is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={item_id} was not found",
        )
    return item


@router.patch("/item/{item_id}")
async def patch_item(item_id: int, new_item_fields: PatchItem, response: Response) -> Item:
    item_before = get_item_by_id(item_id)
    if item_before is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={item_id} was not found",
        )

    item = patch_item_query(item_id, new_item_fields)
    if item.deleted:
        response.status_code = HTTPStatus.NOT_MODIFIED
        response.body = None
    return item


@router.put("/item/{item_id}")
async def put_item(item_id: int, new_item_fields: BaseItem) -> Item:
    item_before = get_item_by_id(item_id)
    if item_before is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={item_id} was not found",
        )
    item = put_item_query(item_id, new_item_fields)
    return item


