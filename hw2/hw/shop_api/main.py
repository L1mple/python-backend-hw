from fastapi import FastAPI, HTTPException, Query, status, Response
from typing import List, Optional, Dict
from pydantic import BaseModel, ConfigDict
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

items: Dict[int, dict] = {}
carts: Dict[int, dict] = {}
item_counter = 0
cart_counter = 0

class ItemIn(BaseModel):
    name: str
    price: float

class ItemOut(ItemIn):
    id: int
    deleted: bool = False

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    model_config = ConfigDict(extra="forbid")

class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float

def get_item_or_404(item_id: int, allow_deleted: bool = False) -> dict:
    item = items.get(item_id)
    if not item or (item["deleted"] and not allow_deleted):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item

def get_cart_or_404(cart_id: int) -> dict:
    cart = carts.get(cart_id)
    if not cart:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart not found")
    return cart

def cart_to_out(cart: CartItemOut) -> CartItemOut:
    out_items = []
    for item_id, quantity in cart["items"].items():
        item = items.get(item_id)
        if not item:
            continue
        out_items.append({
            "id": item_id,
            "name": item["name"],
            "quantity": quantity,
            "available": not item["deleted"],
        })
    price = sum(items[x["id"]]["price"] * x["quantity"]
                for x in out_items if x["available"])
    return {
        "id": cart["id"],
        "items": out_items,
        "price": price,
    }

@app.post("/cart", status_code=status.HTTP_201_CREATED)
def post_cart(response: Response):
    global cart_counter
    cart_counter += 1
    carts[cart_counter] = {"id": cart_counter, "items": {}}
    response.headers["location"] = f"/cart/{cart_counter}"
    return {"id": cart_counter}

@app.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int):
    cart = get_cart_or_404(cart_id)
    return cart_to_out(cart)

@app.get("/cart", response_model=List[CartOut])
def get_cart_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    res = []
    for cart in carts.values():
        out = cart_to_out(cart)
        total_q = sum(i["quantity"] for i in out["items"] if i["available"])
        if min_price is not None and out["price"] < min_price:
            continue
        if max_price is not None and out["price"] > max_price:
            continue
        if min_quantity is not None and total_q < min_quantity:
            continue
        if max_quantity is not None and total_q > max_quantity:
            continue
        res.append(out)
    return res[offset:offset+limit]

@app.post("/cart/{cart_id}/add/{item_id}")
def cart_add(cart_id: int, item_id: int):
    cart = get_cart_or_404(cart_id)
    cart["items"].setdefault(item_id, 0)
    cart["items"][item_id] += 1
    return {"cart_id": cart_id, "item_id": item_id, "quantity": cart["items"][item_id]}

@app.post("/item", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def add_item(item: ItemIn, response: Response):
    global item_counter
    item_counter += 1
    new_item = {"id": item_counter, "name": item.name, "price": item.price, "deleted": False}
    items[item_counter] = new_item
    response.headers["location"] = f"/item/{item_counter}"
    return new_item

@app.get("/item/{item_id}", response_model=ItemOut)
def get_item(item_id: int):
    item = get_item_or_404(item_id)
    return item

@app.get("/item", response_model=List[ItemOut])
def get_item_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
):
    result = []
    for item in items.values():
        if not show_deleted and item["deleted"]:
            continue
        if min_price is not None and item["price"] < min_price:
            continue
        if max_price is not None and item["price"] > max_price:
            continue
        result.append(item)
    return result[offset:offset+limit]

@app.put("/item/{item_id}", response_model=ItemOut)
def replace_item(item_id: int, item_in: ItemIn):
    item = get_item_or_404(item_id)
    item["name"] = item_in.name
    item["price"] = item_in.price
    return item

@app.patch("/item/{item_id}", response_model=ItemOut, status_code=status.HTTP_200_OK)
def patch_item(item_id: int, item_patch: ItemPatch):
    item = items.get(item_id)
    if not item or item["deleted"]:
        if not item:
            raise HTTPException(404, "Item not found")
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    if item_patch.name is not None:
        item["name"] = item_patch.name
    if item_patch.price is not None:
        item["price"] = item_patch.price
    return item

@app.delete("/item/{item_id}", response_model=ItemOut)
def delete_item(item_id: int):
    item = items.get(item_id)
    if item is None:
        return Response(status_code=status.HTTP_200_OK)
    item["deleted"] = True
    return item
