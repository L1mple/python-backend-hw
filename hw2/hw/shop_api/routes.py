from http import HTTPStatus

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import JSONResponse
from shop_api.db import get_session
from shop_api.models import (BaseItem, Cart, CartFilters, Item, ItemFilters,
                             PatchItem)
from shop_api.orm_queries import (add_item, add_to_cart, create_empty_cart,
                                  delete_item_by_id, get_cart_by_id,
                                  get_carts_filtered, get_item_by_id,
                                  get_items_filtered, patch_item_query,
                                  put_item_query)
from sqlalchemy.orm import Session

router = APIRouter()


@router.post("/cart")
async def create_cart(sess: Session = Depends(get_session)):
    cart = create_empty_cart(sess)
    return JSONResponse(content={"id": cart.id}, status_code=HTTPStatus.CREATED,
                        headers={"location": f"/cart/{cart.id}"})


@router.get("/cart/{cart_id}")
async def get_cart(cart_id: int, sess: Session = Depends(get_session)) -> Cart:
    cart = get_cart_by_id(cart_id, sess)
    if cart is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart with id={cart_id} was not found",
        )
    return cart


@router.post("/item", status_code=HTTPStatus.CREATED)
async def create_item(item: BaseItem, response: Response, sess: Session = Depends(get_session)) -> Item:
    _item = add_item(item, sess)
    response.headers["location"] = f"/item/{_item.id}"
    return _item


@router.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int, sess: Session = Depends(get_session)) -> Cart:
    cart = add_to_cart(cart_id, item_id, sess)
    if cart is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Could not add item to cart; either item or cart not found",
        )
    return cart


@router.get("/item/{item_id}")
async def get_item(item_id: int, sess: Session = Depends(get_session)) -> Item:
    item = get_item_by_id(item_id, sess)
    if item is None or item.deleted:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={item_id} was not found",
        )
    return item


@router.get("/cart")
async def get_carts_with_filters(filter_params: CartFilters = Depends(), sess: Session = Depends(get_session)) -> list[Cart]:
    carts = get_carts_filtered(filter_params, sess)
    return carts


@router.get("/item")
async def get_items_with_filters(filter_params: ItemFilters = Depends(), sess: Session = Depends(get_session)) -> list[Item]:
    items = get_items_filtered(filter_params, sess)
    return items


@router.delete("/item/{item_id}")
async def delete_item(item_id: int, sess: Session = Depends(get_session)) -> Item:
    item = delete_item_by_id(item_id, sess)
    if item is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={item_id} was not found",
        )
    return item


@router.patch("/item/{item_id}")
async def patch_item(item_id: int, new_item_fields: PatchItem, response: Response, sess: Session = Depends(get_session)) -> Item:
    item_before = get_item_by_id(item_id, sess)
    if item_before is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={item_id} was not found",
        )

    item = patch_item_query(item_id, new_item_fields, sess)
    if item.deleted:
        response.status_code = HTTPStatus.NOT_MODIFIED
        response.body = None
    return item


@router.put("/item/{item_id}")
async def put_item(item_id: int, new_item_fields: BaseItem, sess: Session = Depends(get_session)) -> Item:
    item_before = get_item_by_id(item_id, sess)
    if item_before is None:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item with id={item_id} was not found",
        )
    item = put_item_query(item_id, new_item_fields, sess)
    return item


