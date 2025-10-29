from http import HTTPStatus
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, NonNegativeInt, PositiveInt, PositiveFloat, ConfigDict

app = FastAPI(title="Shop API")

# ---- Models ----

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    price: PositiveFloat

class ItemPut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    price: PositiveFloat

class ItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")  # лишние поля -> 422
    name: Optional[str] = None
    price: Optional[PositiveFloat] = None

# ---- In-memory stores ----

_items: Dict[int, Item] = {}
_item_id = 0

def _next_item_id() -> int:
    global _item_id
    _item_id += 1
    return _item_id

_carts: Dict[int, Dict[int, int]] = {}
_cart_id = 0

def _next_cart_id() -> int:
    global _cart_id
    _cart_id += 1
    return _cart_id

def _item_visible(item: Item, show_deleted: bool) -> bool:
    return show_deleted or not item.deleted

# ---- Item endpoints ----

@app.post("/item", status_code=HTTPStatus.CREATED)
async def create_item(body: ItemCreate):
    item_id = _next_item_id()
    item = Item(id=item_id, name=body.name, price=float(body.price), deleted=False)
    _items[item_id] = item
    return item.model_dump()

@app.get("/item/{id}")
async def get_item(id: int):
    item = _items.get(id)
    if item is None or item.deleted:
        raise HTTPException(HTTPStatus.NOT_FOUND)
    return item.model_dump()

@app.get("/item")
async def list_items(
    offset: NonNegativeInt = 0,
    limit: Optional[PositiveInt] = None,
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    show_deleted: bool = False,
):
    items = [i for i in _items.values() if _item_visible(i, show_deleted)]
    if min_price is not None:
        items = [i for i in items if i.price >= float(min_price)]
    if max_price is not None:
        items = [i for i in items if i.price <= float(max_price)]
    items.sort(key=lambda x: x.id)
    sliced = items[offset:] if limit is None else items[offset : offset + limit]
    return [i.model_dump() for i in sliced]

@app.put("/item/{id}")
async def put_item(id: int, body: ItemPut):
    item = _items.get(id)
    if item is None or item.deleted:
        raise HTTPException(HTTPStatus.NOT_MODIFIED)
    item.name = body.name
    item.price = float(body.price)
    _items[id] = item
    return item.model_dump()

@app.patch("/item/{id}")
async def patch_item(id: int, body: ItemPatch):
    item = _items.get(id)
    if item is None or item.deleted:
        raise HTTPException(HTTPStatus.NOT_MODIFIED)
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        return item.model_dump()
    if "name" in updates:
        item.name = updates["name"]
    if "price" in updates:
        item.price = float(updates["price"])
    _items[id] = item
    return item.model_dump()

@app.delete("/item/{id}")
async def delete_item(id: int):
    item = _items.get(id)
    if item is None:
        return Response("")
    if not item.deleted:
        item.deleted = True
        _items[id] = item
    return Response("")

# ---- Cart helpers ----

def _cart_total_price(cart_items: Dict[int, int]) -> float:
    total = 0.0
    for item_id, qty in cart_items.items():
        item = _items.get(item_id)
        if item and not item.deleted:
            total += item.price * qty
    return float(total)

def _cart_items_repr(cart_items: Dict[int, int]) -> List[dict]:
    return [{"id": iid, "quantity": qty} for iid, qty in cart_items.items()]

# ---- Cart endpoints ----

@app.post("/cart", status_code=HTTPStatus.CREATED)
async def create_cart(response: Response):
    cart_id = _next_cart_id()
    _carts[cart_id] = {}
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}

@app.get("/cart/{id}")
async def get_cart(id: int):
    cart = _carts.get(id)
    if cart is None:
        raise HTTPException(HTTPStatus.NOT_FOUND)
    return {
        "id": id,
        "items": _cart_items_repr(cart),
        "price": _cart_total_price(cart),
    }

@app.post("/cart/{id}/add/{item_id}")
async def add_item_to_cart(id: int, item_id: int):
    cart = _carts.get(id)
    if cart is None:
        raise HTTPException(HTTPStatus.NOT_FOUND)
    cart[item_id] = cart.get(item_id, 0) + 1
    return {"id": id, "items": _cart_items_repr(cart), "price": _cart_total_price(cart)}

@app.get("/cart")
async def list_carts(
    offset: NonNegativeInt = 0,
    limit: Optional[PositiveInt] = None,
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    min_quantity: Optional[NonNegativeInt] = None,
    max_quantity: Optional[NonNegativeInt] = None,
):
    carts_list = sorted(_carts.items(), key=lambda x: x[0])
    filtered: List[tuple[int, Dict[int, int]]] = []
    for cid, cart in carts_list:
        price = _cart_total_price(cart)
        if min_price is not None and price < float(min_price):
            continue
        if max_price is not None and price > float(max_price):
            continue
        filtered.append((cid, cart))

    if min_quantity is not None or max_quantity is not None:
        agg = 0
        constrained: List[tuple[int, Dict[int, int]]] = []
        for cid, cart in filtered:
            cart_qty = sum(cart.values())
            if max_quantity is not None and agg + cart_qty > max_quantity:
                break
            constrained.append((cid, cart))
            agg += cart_qty
        filtered = constrained

    sliced = filtered[offset:] if limit is None else filtered[offset : offset + limit]
    return [{"id": cid, "items": _cart_items_repr(cart), "price": _cart_total_price(cart)} for cid, cart in sliced]
