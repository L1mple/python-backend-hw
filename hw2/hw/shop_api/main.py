from fastapi import FastAPI, HTTPException, Response
from typing import Optional, Annotated
from pydantic import Field
from http import HTTPStatus

from shop_api.models import ItemCreate, ItemUpdate
from shop_api.storage import storage


app = FastAPI(title="Shop API")


@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(item: ItemCreate):
    new_item = storage.create_item(item.name, item.price)
    return new_item


@app.get("/item/{id}", status_code=HTTPStatus.OK)
def get_item(id: int):
    item = storage.get_item(id)

    if item is None or item['deleted']:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    return item


@app.get("/item", status_code=HTTPStatus.OK)
def get_items(
    offset: Annotated[int, Field(ge=0)] = 0,
    limit: Annotated[int, Field(gt=0)] = 10,
    min_price: Annotated[Optional[float], Field(ge=0)] = None,
    max_price: Annotated[Optional[float], Field(ge=0)] = None,
    show_deleted: bool = False
):
    items = storage.get_all_items(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted
    )
    return items


@app.put("/item/{id}", status_code=HTTPStatus.OK)
def replace_item(id: int, item: ItemCreate):
    existing_item = storage.get_item(id)

    if existing_item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    if existing_item['deleted']:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)

    updated_item = storage.replace_item(id, item.name, item.price)
    return updated_item


@app.patch("/item/{id}", status_code=HTTPStatus.OK)
def patch_item(id: int, item: ItemUpdate):
    existing_item = storage.get_item(id)

    if existing_item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    if existing_item['deleted']:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)

    updated_item = storage.update_item(id, item.name, item.price)
    return updated_item


@app.delete("/item/{id}", status_code=HTTPStatus.OK)
def delete_item(id: int):
    item = storage.get_item(id)

    if item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    deleted_item = storage.delete_item(id)
    return deleted_item



@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    cart_id = storage.create_cart()
    response.headers["location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@app.get("/cart/{id}", status_code=HTTPStatus.OK)
def get_cart(id: int):
    cart = storage.get_cart(id)

    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

    return cart


@app.get("/cart", status_code=HTTPStatus.OK)
def get_carts(
    offset: Annotated[int, Field(ge=0)] = 0,
    limit: Annotated[int, Field(gt=0)] = 10,
    min_price: Annotated[Optional[float], Field(ge=0)] = None,
    max_price: Annotated[Optional[float], Field(ge=0)] = None,
    min_quantity: Annotated[Optional[int], Field(ge=0)] = None,
    max_quantity: Annotated[Optional[int], Field(ge=0)] = None,
):
    carts = storage.get_all_carts(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity
    )
    return carts


@app.post("/cart/{cart_id}/add/{item_id}", status_code=HTTPStatus.OK)
def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in storage.carts:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

    item = storage.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    success = storage.add_item_to_cart(cart_id, item_id)

    if not success:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Failed to add item to cart")

    return {"message": "Item added to cart successfully"}
