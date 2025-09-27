import http
import itertools
import typing

from fastapi import FastAPI, HTTPException, Response, Query

import shop_api.schemas as schemas

app = FastAPI(title="Shop API")


class Store:
    def __init__(self):
        self.items: dict[int, schemas.Item] = {}
        self.carts: dict[int, schemas.Cart] = {}

        self.next_item = 1
        self.next_cart = 1


store = Store()


@app.post("/cart", status_code=http.HTTPStatus.CREATED)
async def create_cart(response: Response) -> schemas.WrappedID:
    cart_id = store.next_cart
    store.carts[cart_id] = schemas.Cart(id=cart_id, items={})
    store.next_cart += 1
    data = schemas.WrappedID(id=cart_id)
    response.headers["location"] = f"/cart/{cart_id}"
    return data


@app.get("/cart/{cart_id}")
async def get_cart(cart_id: int) -> schemas.CartResponse:
    if cart_id not in store.carts:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return store.carts[cart_id].create_cart_response(store.items)[0]


@app.get("/cart")
async def get_carts(
    filter: typing.Annotated[schemas.GetCartsRequest, Query()],
) -> list[schemas.CartResponse]:
    prepared_carts: typing.Generator[tuple[schemas.CartResponse, int]] = (
        cart.create_cart_response(store.items) for cart in store.carts.values()
    )
    filtered_carts = (
        cart
        for cart, quantity in prepared_carts
        if all(
            (
                (filter.min_price is None or cart.price >= filter.min_price),
                (filter.max_price is None or cart.price <= filter.max_price),
                (filter.min_quantity is None or quantity >= filter.min_quantity),
                (filter.max_quantity is None or quantity <= filter.max_quantity),
            )
        )
    )
    return list(
        itertools.islice(filtered_carts, filter.offset, filter.offset + filter.limit)
    )


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int):
    if cart_id not in store.carts:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    if item_id not in store.items or store.items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    if item_id in store.carts[cart_id].items:
        store.carts[cart_id].items[item_id] += 1
    else:
        store.carts[cart_id].items[item_id] = 0
    return None


@app.post("/item", status_code=http.HTTPStatus.CREATED)
async def create_item(
    payload: schemas.CreateItemRequest, response: Response
) -> schemas.Item:
    item_id = store.next_item
    store.items[item_id] = schemas.Item(
        id=item_id, name=payload.name, price=payload.price, deleted=False
    )
    store.next_item += 1
    response.headers["location"] = f"/item/{item_id}"
    return store.items[item_id]


@app.get("/item/{item_id}")
async def get_item(item_id: int) -> schemas.Item:
    if item_id not in store.items or store.items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return store.items[item_id]


@app.get("/item")
async def get_items(
    filter: typing.Annotated[schemas.GetItemsRequest, Query()],
) -> list[schemas.Item]:
    filtered_items = (
        item
        for item in store.items.values()
        if all(
            (
                (filter.min_price is None or item.price >= filter.min_price),
                (filter.max_price is None or item.price <= filter.max_price),
                (not item.deleted or filter.show_deleted),
            )
        )
    )
    return list(
        itertools.islice(filtered_items, filter.offset, filter.offset + filter.limit)
    )


@app.put("/item/{item_id}")
async def put_item(item_id: int, payload: schemas.CreateItemRequest) -> schemas.Item:
    if item_id not in store.items or store.items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    store.items[item_id].name = payload.name
    store.items[item_id].price = payload.price
    return store.items[item_id]


@app.patch("/item/{item_id}")
async def patch_item(item_id: int, payload: schemas.UpdateItemRequest) -> schemas.Item:
    if item_id not in store.items:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    if store.items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_MODIFIED)
    if payload.name:
        store.items[item_id].name = payload.name
    if payload.price:
        store.items[item_id].price = payload.price
    return store.items[item_id]


@app.delete("/item/{item_id}")
async def delete_item(item_id: int) -> schemas.Item:
    if item_id not in store.items:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    store.items[item_id].deleted = True
    return store.items[item_id]
