from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.params import Query
from fastapi.responses import JSONResponse

app = FastAPI(title="Shop API")
# Expose Prometheus metrics at `/metrics` and instrument default handlers
Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


# In-memory storage
_item_seq: int = 0
_cart_seq: int = 0
ITEMS: Dict[int, dict] = {}
CARTS: Dict[int, dict] = {}


def _next_item_id() -> int:
    global _item_seq
    _item_seq += 1
    return _item_seq


def _next_cart_id() -> int:
    global _cart_seq
    _cart_seq += 1
    return _cart_seq


def _recalc_cart(cart: dict) -> None:
    price = 0.0
    for it in cart["items"]:
        item_id = it["id"]
        qty = it["quantity"]
        item = ITEMS.get(item_id)
        if item is None:
            # If item missing, skip
            continue
        price += float(item["price"]) * qty
        # availability flag
    for it in cart["items"]:
        item = ITEMS.get(it["id"])
        it["available"] = bool(item is not None and (not item.get("deleted", False)))
    cart["price"] = float(price)


# Item endpoints
@app.post("/item")
def create_item(body: dict):
    if not isinstance(body, dict) or "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)
    item_id = _next_item_id()
    item = {
        "id": item_id,
        "name": body["name"],
        "price": float(body["price"]),
        "deleted": False,
    }
    ITEMS[item_id] = item
    return JSONResponse(status_code=201, content=item)


@app.get("/item/{item_id}")
def get_item(item_id: int):
    item = ITEMS.get(item_id)
    if item is None or item.get("deleted"):
        raise HTTPException(status_code=404)
    return item


@app.get("/item")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    show_deleted: bool = False,
):
    data = list(ITEMS.values())
    if not show_deleted:
        data = [x for x in data if not x.get("deleted", False)]
    if min_price is not None:
        data = [x for x in data if float(x["price"]) >= float(min_price)]
    if max_price is not None:
        data = [x for x in data if float(x["price"]) <= float(max_price)]
    return data[offset : offset + limit]


@app.put("/item/{item_id}")
def put_item(item_id: int, body: dict):
    if not isinstance(body, dict) or "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)
    item = ITEMS.get(item_id)
    if item is None:
        raise HTTPException(status_code=404)
    item = item.copy()
    item.update({
        "name": body["name"],
        "price": float(body["price"]),
    })
    ITEMS[item_id] = item
    # update availability in carts
    for cart in CARTS.values():
        _recalc_cart(cart)
    return item


@app.patch("/item/{item_id}")
def patch_item(item_id: int, body: dict):
    item = ITEMS.get(item_id)
    if item is None:
        raise HTTPException(status_code=404)
    if item.get("deleted"):
        return JSONResponse(status_code=304, content=None)
    if any(k not in {"name", "price"} for k in body.keys()):
        raise HTTPException(status_code=422)
    if "name" in body:
        item["name"] = body["name"]
    if "price" in body:
        item["price"] = float(body["price"])
    for cart in CARTS.values():
        _recalc_cart(cart)
    return item


@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    item = ITEMS.get(item_id)
    if item is not None:
        item["deleted"] = True
        for cart in CARTS.values():
            _recalc_cart(cart)
    return {"status": "ok"}


# Cart endpoints
@app.post("/cart")
def create_cart():
    cart_id = _next_cart_id()
    cart = {"id": cart_id, "items": [], "price": 0.0}
    CARTS[cart_id] = cart
    headers = {"location": f"/cart/{cart_id}"}
    return JSONResponse(status_code=201, content={"id": cart_id}, headers=headers)


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int):
    cart = CARTS.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404)
    _recalc_cart(cart)
    return cart


@app.get("/cart")
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
):
    data = list(CARTS.values())
    for cart in data:
        _recalc_cart(cart)
    if min_price is not None:
        data = [c for c in data if float(c["price"]) >= float(min_price)]
    if max_price is not None:
        data = [c for c in data if float(c["price"]) <= float(max_price)]
    if min_quantity is not None:
        data = [
            c for c in data if sum(it["quantity"] for it in c["items"]) >= min_quantity
        ]
    if max_quantity is not None:
        data = [
            c for c in data if sum(it["quantity"] for it in c["items"]) <= max_quantity
        ]
    return data[offset : offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int):
    cart = CARTS.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404)
    item = ITEMS.get(item_id)
    if item is None:
        raise HTTPException(status_code=404)
    for it in cart["items"]:
        if it["id"] == item_id:
            it["quantity"] += 1
            _recalc_cart(cart)
            return {"status": "ok"}
    cart["items"].append(
        {"id": item_id, "name": item["name"], "quantity": 1, "available": not item.get("deleted", False)}
    )
    _recalc_cart(cart)
    return {"status": "ok"}
