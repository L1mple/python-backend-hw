from http import HTTPStatus
from typing import Annotated

from fastapi import (
    FastAPI,
    HTTPException,
    Query,
    Response,
)
from prometheus_fastapi_instrumentator import Instrumentator

from hw import store
from .contracts import (
    ItemCreate,
    ItemPut,
    ItemPatch,
    ItemOut,
    CartOut,
)

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)


@app.post("/cart", status_code=HTTPStatus.CREATED)
def post_cart(response: Response) -> dict[str, int]:
    cart_id = store.post_cart()
    response.headers["location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@app.get(
    "/cart/{cart_id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully found a cart with a given ID",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to find a cart with a given ID"
        }
    }
)
def get_cart(cart_id: int) -> CartOut:
    cart = store.get_cart(cart_id)
    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Requested /cart/{cart_id} wasn't found")
    return CartOut.cart_to_out(cart)


@app.get("/cart")
def get_cart_list(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(gt=0)] = 10,
        min_price: Annotated[float | None, Query(ge=0)] = None,
        max_price: Annotated[float | None, Query(ge=0)] = None,
        min_quantity: Annotated[int | None, Query(ge=0)] = None,
        max_quantity: Annotated[int | None, Query(ge=0)] = None,
) -> list[CartOut]:
    carts = store.get_carts_list(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )
    return [CartOut.cart_to_out(cart) for cart in carts]


@app.post(
    "/cart/{cart_id}/add/{item_id}",
    responses={
        HTTPStatus.NOT_FOUND: {
            "description": "Requested cart_id or item_id wasn't found",
        },
    }
)
def post_add_to_cart(cart_id: int, item_id: int) -> CartOut:
    cart = store.get_cart(cart_id)
    if cart is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Requested /cart/{cart_id} wasn't found"
        )
    item = store.get_item(item_id)
    if item is None:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=f"Requested /cart/{cart_id}/add/{item_id} wasn't found"
        )
    store.add_item_to_cart(cart_id, item_id)
    return CartOut.cart_to_out(store.get_cart(cart_id))


@app.post("/item", status_code=HTTPStatus.CREATED)
def post_item(body: ItemCreate) -> ItemOut:
    item_id = store.post_item(name=body.name, price=body.price)
    item = store.get_item(item_id)
    return ItemOut.item_to_out(item)


@app.get(
    "/item/{item_id}",
    responses={
        HTTPStatus.NOT_FOUND: {
            "description": "Requested item_id wasn't found",
        },
    }
)
def get_item(item_id: int) -> ItemOut:
    item = store.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Requested /item/{item_id} wasn't found")
    return ItemOut.item_to_out(item)


@app.get("/item")
def get_items(
        offset: Annotated[int, Query(ge=0)] = 0,
        limit: Annotated[int, Query(gt=0)] = 10,
        min_price: Annotated[float | None, Query(ge=0)] = None,
        max_price: Annotated[float | None, Query(ge=0)] = None,
        show_deleted: bool = False,
) -> list[ItemOut]:
    items = store.get_items_list(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )
    return [ItemOut.item_to_out(item) for item in items]


@app.put("/item/{item_id}")
def put_item(item_id: int, body: ItemPut) -> ItemOut:
    item = store.put_item(item_id=item_id, name=body.name, price=body.price)
    if item is None:
        raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    return ItemOut.item_to_out(item)


@app.patch("/item/{item_id}")
def patch_item(item_id: int, body: ItemPatch):
    item = store.patch_item(item_id=item_id, name=body.name, price=body.price)
    if item is None:
        # tests expect NOT_MODIFIED for deleted only
        orig = store.get_item_including_deleted(item_id)
        if orig is not None and orig.deleted is True:
            return Response(status_code=HTTPStatus.NOT_MODIFIED)
        raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    return ItemOut.item_to_out(item)


@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    store.delete_item(item_id)
    return Response(status_code=HTTPStatus.OK)
