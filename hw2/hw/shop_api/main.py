from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException
from prometheus_fastapi_instrumentator import Instrumentator
from fastapi.params import Query
from fastapi.responses import JSONResponse

from .db import engine, session_scope
from .models import Base, Item, Cart, CartItem

app = FastAPI(title="Shop API")
# Expose Prometheus metrics at `/metrics` and instrument default handlers
Instrumentator().instrument(app).expose(app)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


Base.metadata.create_all(bind=engine)


def _recalc_cart_dict(cart: dict) -> None:
    price = 0.0
    for it in cart["items"]:
        price += float(it["price"]) * it["quantity"]
        it["available"] = not it.get("deleted", False)
    cart["price"] = float(price)


# Item endpoints
@app.post("/item")
def create_item(body: dict):
    if not isinstance(body, dict) or "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)
    with session_scope() as s:
        obj = Item(name=body["name"], price=float(body["price"]))
        s.add(obj)
        s.flush()
        return JSONResponse(status_code=201, content={
            "id": obj.id,
            "name": obj.name,
            "price": float(obj.price),
            "deleted": bool(obj.deleted),
        })


@app.get("/item/{item_id}")
def get_item(item_id: int):
    with session_scope() as s:
        obj = s.get(Item, item_id)
        if obj is None or obj.deleted:
            raise HTTPException(status_code=404)
        return {"id": obj.id, "name": obj.name, "price": float(obj.price), "deleted": bool(obj.deleted)}


@app.get("/item")
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    show_deleted: bool = False,
):
    from sqlalchemy import select
    with session_scope() as s:
        stmt = select(Item)
        if not show_deleted:
            stmt = stmt.where(Item.deleted.is_(False))
        if min_price is not None:
            from sqlalchemy import cast, Float
            stmt = stmt.where(Item.price >= float(min_price))
        if max_price is not None:
            stmt = stmt.where(Item.price <= float(max_price))
        rows = s.execute(stmt.offset(offset).limit(limit)).scalars().all()
        return [{"id": r.id, "name": r.name, "price": float(r.price), "deleted": bool(r.deleted)} for r in rows]


@app.put("/item/{item_id}")
def put_item(item_id: int, body: dict):
    if not isinstance(body, dict) or "name" not in body or "price" not in body:
        raise HTTPException(status_code=422)
    with session_scope() as s:
        obj = s.get(Item, item_id)
        if obj is None:
            raise HTTPException(status_code=404)
        obj.name = body["name"]
        obj.price = float(body["price"])
        s.flush()
        return {"id": obj.id, "name": obj.name, "price": float(obj.price), "deleted": bool(obj.deleted)}


@app.patch("/item/{item_id}")
def patch_item(item_id: int, body: dict):
    with session_scope() as s:
        obj = s.get(Item, item_id)
        if obj is None:
            raise HTTPException(status_code=404)
        if obj.deleted:
            return JSONResponse(status_code=304, content=None)
        if any(k not in {"name", "price"} for k in body.keys()):
            raise HTTPException(status_code=422)
        if "name" in body:
            obj.name = body["name"]
        if "price" in body:
            obj.price = float(body["price"])
        s.flush()
        return {"id": obj.id, "name": obj.name, "price": float(obj.price), "deleted": bool(obj.deleted)}


@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    with session_scope() as s:
        obj = s.get(Item, item_id)
        if obj is not None:
            obj.deleted = True
            s.flush()
        return {"status": "ok"}


# Cart endpoints
@app.post("/cart")
def create_cart():
    with session_scope() as s:
        cart = Cart()
        s.add(cart)
        s.flush()
        headers = {"location": f"/cart/{cart.id}"}
        return JSONResponse(status_code=201, content={"id": cart.id}, headers=headers)


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int):
    with session_scope() as s:
        cart = s.get(Cart, cart_id)
        if cart is None:
            raise HTTPException(status_code=404)
        items = []
        price = 0.0
        for ci in cart.items:
            items.append({
                "id": ci.item_id,
                "name": ci.item.name,
                "quantity": ci.quantity,
                "available": not ci.item.deleted,
                "price": float(ci.item.price),
                "deleted": bool(ci.item.deleted),
            })
            price += float(ci.item.price) * ci.quantity
        return {"id": cart.id, "items": items, "price": float(price)}


@app.get("/cart")
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
):
    from sqlalchemy import select, func
    with session_scope() as s:
        carts = s.execute(select(Cart).offset(offset).limit(limit)).scalars().all()
        result = []
        for cart in carts:
            items = []
            price = 0.0
            total_qty = 0
            for ci in cart.items:
                items.append({
                    "id": ci.item_id,
                    "name": ci.item.name,
                    "quantity": ci.quantity,
                    "available": not ci.item.deleted,
                    "price": float(ci.item.price),
                    "deleted": bool(ci.item.deleted),
                })
                price += float(ci.item.price) * ci.quantity
                total_qty += ci.quantity
            data_cart = {"id": cart.id, "items": items, "price": float(price)}
            if (min_price is not None and price < float(min_price)) or (
                max_price is not None and price > float(max_price)
            ) or (
                min_quantity is not None and total_qty < min_quantity
            ) or (
                max_quantity is not None and total_qty > max_quantity
            ):
                continue
            result.append(data_cart)
        return result


@app.post("/cart/{cart_id}/add/{item_id}")
def add_to_cart(cart_id: int, item_id: int):
    with session_scope() as s:
        cart = s.get(Cart, cart_id)
        if cart is None:
            raise HTTPException(status_code=404)
        item = s.get(Item, item_id)
        if item is None:
            raise HTTPException(status_code=404)
        # find existing
        existing = next((ci for ci in cart.items if ci.item_id == item_id), None)
        if existing:
            existing.quantity += 1
        else:
            cart.items.append(CartItem(item_id=item_id, quantity=1))
        s.flush()
        return {"status": "ok"}
