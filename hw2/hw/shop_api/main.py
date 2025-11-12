from fastapi import FastAPI, HTTPException, Query, Response
from http import HTTPStatus
from typing import Optional, Dict, Any

from store import queries
from store.models import Item, Cart

app = FastAPI(title="Shop API")

@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(item: Item):
    created_item = queries.create_item(item.name, item.price)
    if hasattr(created_item, "dict"):
        created_item = created_item.model_dump()
    elif not isinstance(created_item, dict):
        created_item = vars(created_item)

    if "id" not in created_item:
        created_item["id"] = queries.get_last_item_id()
        if not created_item["id"]:
            created_item["id"] = len(queries.list_items())

    created_item["deleted"] = created_item.get("deleted", False)

    return created_item


@app.get("/item/{item_id}", status_code=HTTPStatus.OK)
def get_item(item_id: int):
    item = queries.get_item(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@app.get("/item", status_code=HTTPStatus.OK)
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
):
    items = queries.list_items()
    if not show_deleted:
        items = [i for i in items if not i.deleted]
    if min_price is not None:
        items = [i for i in items if i.price >= min_price]
    if max_price is not None:
        items = [i for i in items if i.price <= max_price]
    return items[offset:offset + limit]


@app.put("/item/{item_id}")
def replace_item(item_id: int, body: Dict[str, Any]):
    if "name" not in body or "price" not in body:
        raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY)
    item = queries.get_item(item_id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    updated = queries.replace_item(item_id, Item(id=item_id, **body))
    return updated


@app.patch("/item/{item_id}")
def patch_item(item_id: int, body: Dict[str, Any], response: Response):
    item = queries.get_item(item_id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    if item.deleted:
        response.status_code = HTTPStatus.NOT_MODIFIED
        return item

    invalid_keys = [k for k in body if k not in {"name", "price"}]
    if invalid_keys:
        raise HTTPException(status_code=HTTPStatus.UNPROCESSABLE_ENTITY)

    updated = queries.patch_item(item_id, body)
    return updated


@app.delete("/item/{item_id}", status_code=HTTPStatus.OK)
def delete_item(item_id: int):
    deleted = queries.delete_item(item_id)
    return {"status": "deleted" if deleted else "already deleted"}

@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    cart = queries.create_cart()
    response.headers["Location"] = f"/cart/{cart.id}"
    return {"id": cart.id}


@app.get("/cart/{cart_id}", status_code=HTTPStatus.OK)
def get_cart(cart_id: int):
    cart = queries.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return cart


@app.get("/cart", status_code=HTTPStatus.OK)
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    carts = queries.list_carts()

    def total_quantity(cart):
        return sum(i.quantity for i in cart.items)

    if min_price is not None:
        carts = [c for c in carts if c.price >= min_price]
    if max_price is not None:
        carts = [c for c in carts if c.price <= max_price]
    if min_quantity is not None:
        carts = [c for c in carts if total_quantity(c) >= min_quantity]
    if max_quantity is not None:
        carts = [c for c in carts if total_quantity(c) <= max_quantity]

    return carts[offset:offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    cart = queries.add_to_cart(cart_id, item_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return cart
