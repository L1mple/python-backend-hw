from __future__ import annotations
from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, PositiveInt, NonNegativeInt, Field
from http import HTTPStatus

app = FastAPI(title="Online Store API")

items: dict[int, dict] = {}
carts: dict[int, dict] = {}
next_item_id = 1
next_cart_id = 1

class ItemCreate(BaseModel):
    name: str
    price: float = Field(ge=0.0)

class ItemResponse(ItemCreate):
    id: int
    deleted: bool = False

class ItemPatch(BaseModel):
    name: str | None = None
    price: float | None = Field(None, ge=0.0)

    class Config:
        extra = "forbid"

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: list[CartItem]
    total_price: float

@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(item: ItemCreate, response: Response):
    global next_item_id
    item_id = next_item_id
    next_item_id += 1

    data = item.dict() | {"id": item_id, "deleted": False}
    items[item_id] = data

    response.headers["location"] = f"/item/{item_id}"
    return data

@app.get("/item/{id}")
def get_item(id: int):
    item = items.get(id)
    if not item or item["deleted"]:
        raise HTTPException(HTTPStatus.NOT_FOUND)
    return item

@app.get("/item")
def list_items(
    offset: NonNegativeInt = 0,
    limit: PositiveInt = 10,
    min_price: float | None = Query(None, ge=0.0),
    max_price: float | None = Query(None, ge=0.0),
    show_deleted: bool = False,
):
    result = list(items.values())
    if not show_deleted:
        result = [i for i in result if not i["deleted"]]
    if min_price is not None:
        result = [i for i in result if i["price"] >= min_price]
    if max_price is not None:
        result = [i for i in result if i["price"] <= max_price]

    return result[offset: offset + limit]

@app.put("/item/{id}")
def put_item(id: int, body: ItemCreate):
    if id not in items or items[id]["deleted"]:
        raise HTTPException(HTTPStatus.NOT_MODIFIED)
    items[id].update(body.dict())
    return items[id]

@app.patch("/item/{id}")
def patch_item(id: int, body: ItemPatch):
    if id not in items or items[id]["deleted"]:
        raise HTTPException(HTTPStatus.NOT_MODIFIED)

    if "deleted" in body.model_dump():
        raise HTTPException(HTTPStatus.UNPROCESSABLE_ENTITY)

    for k, v in body.dict(exclude_unset=True).items():
        items[id][k] = v
    return items[id]

@app.delete("/item/{id}")
def delete_item(id: int):
    if id in items:
        items[id]["deleted"] = True
    return {"ok": True}

@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    global next_cart_id
    cid = next_cart_id
    next_cart_id += 1
    carts[cid] = {"id": cid, "items": []}
    response.headers["location"] = f"/cart/{cid}"
    return {"id": cid}

@app.get("/cart/{id}")
def get_cart(id: int):
    cart = carts.get(id)
    if not cart:
        raise HTTPException(HTTPStatus.NOT_FOUND)

    result_items = []
    total = 0.0
    for entry in cart["items"]:
        item = items.get(entry["id"])
        available = item is not None and not item["deleted"]
        price = item["price"] if available else 0
        total += price * entry["quantity"]
        result_items.append({
            "id": entry["id"],
            "name": entry["name"],
            "quantity": entry["quantity"],
            "available": available,
        })

    return {"id": id, "items": result_items, "total_price": total}

@app.get("/cart")
def list_carts(
    offset: NonNegativeInt = 0,
    limit: PositiveInt = 10,
    min_price: float | None = Query(None, ge=0.0),
    max_price: float | None = Query(None, ge=0.0),
    min_quantity: int | None = Query(None, ge=0),
    max_quantity: int | None = Query(None, ge=0),
):
    carts_list = []
    for cart in carts.values():
        data = get_cart(cart["id"])
        total_quantity = sum(i["quantity"] for i in data["items"])
        if min_price is not None and data["total_price"] < min_price:
            continue
        if max_price is not None and data["total_price"] > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        carts_list.append(data)

    return carts_list[offset: offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts:
        raise HTTPException(HTTPStatus.NOT_FOUND)
    if item_id not in items:
        raise HTTPException(HTTPStatus.NOT_FOUND)

    cart = carts[cart_id]
    for entry in cart["items"]:
        if entry["id"] == item_id:
            entry["quantity"] += 1
            break
    else:
        cart["items"].append(
            {"id": item_id, "name": items[item_id]["name"], "quantity": 1}
        )

    return {"id": cart_id, "items": cart["items"]}
