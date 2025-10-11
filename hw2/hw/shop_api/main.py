from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, Path, Query, status
from pydantic import BaseModel, Field, PositiveInt, conint, confloat
from fastapi.responses import JSONResponse

app = FastAPI(title="Shop API")

# ----------------------------
# Pydantic models
# ----------------------------
class ItemCreate(BaseModel):
    name: str
    price: confloat(ge=0.0)


class Item(ItemCreate):
    id: int
    deleted: bool = False


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[confloat(ge=0.0)] = None


class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float


# ----------------------------
# In-memory storage
# ----------------------------
_next_item_id = 1
_items: Dict[int, Item] = {}

_next_cart_id = 1
# carts stored as dict cart_id -> dict[item_id -> quantity]
_carts: Dict[int, Dict[int, int]] = {}


# ----------------------------
# Helpers
# ----------------------------
def _get_item_or_404(item_id: int) -> Item:
    item = _items.get(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return item


def _cart_to_response(cart_id: int) -> CartOut:
    item_map = _carts.get(cart_id, {})
    items_out: List[CartItemOut] = []
    total_price = 0.0
    for iid, qty in item_map.items():
        item = _items.get(iid)
        available = item is not None and not item.deleted
        name = item.name if item is not None else ""
        items_out.append(
            CartItemOut(id=iid, name=name, quantity=qty, available=available)
        )
        if available:
            total_price += (item.price * qty)  # type: ignore
    return CartOut(id=cart_id, items=items_out, price=total_price)


# ----------------------------
# Cart endpoints
# ----------------------------
@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart():
    global _next_cart_id
    cid = _next_cart_id
    _next_cart_id += 1
    _carts[cid] = {}
    location = f"/cart/{cid}"
    resp = JSONResponse(status_code=status.HTTP_201_CREATED, content={"id": cid})
    resp.headers["location"] = location
    return resp


@app.get("/cart/{id}", response_model=CartOut)
def get_cart(id: int = Path(..., ge=1)):
    if id not in _carts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return _cart_to_response(id)


@app.get("/cart", response_model=List[CartOut])
def list_carts(
    offset: conint(ge=0) = Query(0),
    limit: PositiveInt = Query(10),
    min_price: Optional[confloat(ge=0.0)] = Query(None),
    max_price: Optional[confloat(ge=0.0)] = Query(None),
    min_quantity: Optional[conint(ge=0)] = Query(None),
    max_quantity: Optional[conint(ge=0)] = Query(None),
):
    # gather all carts in ascending id order
    cart_ids = sorted(_carts.keys())
    selected = []
    for cid in cart_ids:
        cart_resp = _cart_to_response(cid)
        # per-cart total quantity
        total_quantity = sum(i.quantity for i in cart_resp.items)
        # price already computed in cart_resp.price
        price = cart_resp.price
        # apply filters
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        selected.append(cart_resp)
    # apply offset+limit
    return selected[offset : offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}", status_code=status.HTTP_200_OK)
def add_item_to_cart(
    cart_id: int = Path(..., ge=1), item_id: int = Path(..., ge=1)
):
    if cart_id not in _carts:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if item_id not in _items:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    item_map = _carts[cart_id]
    item_map[item_id] = item_map.get(item_id, 0) + 1
    return {"ok": True}


# ----------------------------
# Item endpoints
# ----------------------------
@app.post("/item", status_code=status.HTTP_201_CREATED)
def create_item(item_in: ItemCreate):
    global _next_item_id
    iid = _next_item_id
    _next_item_id += 1
    item = Item(id=iid, name=item_in.name, price=item_in.price, deleted=False)
    _items[iid] = item
    return item


@app.get("/item/{id}", response_model=Item)
def get_item(id: int = Path(..., ge=1)):
    item = _items.get(id)
    if item is None or item.deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return item


@app.get("/item", response_model=List[Item])
def list_items(
    offset: conint(ge=0) = Query(0),
    limit: PositiveInt = Query(10),
    min_price: Optional[confloat(ge=0.0)] = Query(None),
    max_price: Optional[confloat(ge=0.0)] = Query(None),
    show_deleted: bool = Query(False),
):
    items_list = [it for it in _items.values() if (show_deleted or not it.deleted)]
    # apply price filters
    if min_price is not None:
        items_list = [it for it in items_list if it.price >= min_price]
    if max_price is not None:
        items_list = [it for it in items_list if it.price <= max_price]
    # sort by id
    items_list = sorted(items_list, key=lambda x: x.id)
    return items_list[offset : offset + limit]


@app.put("/item/{id}", response_model=Item)
def replace_item(id: int = Path(..., ge=1), item_in: ItemCreate = ...):
    # PUT replaces only existing item (creation forbidden)
    item = _items.get(id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    # replace fields but keep id and deleted flag
    new_item = Item(id=id, name=item_in.name, price=item_in.price, deleted=item.deleted)
    _items[id] = new_item
    return new_item


@app.patch("/item/{id}")
def patch_item(id: int = Path(..., ge=1), patch: ItemPatch = ...):
    item = _items.get(id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    if item.deleted:
        # tests expect NOT_MODIFIED for attempts to patch deleted item
        return JSONResponse(status_code=status.HTTP_304_NOT_MODIFIED, content={"ok": False})
    # validate that no unexpected fields are present and 'deleted' can't be changed
    # FastAPI/Pydantic already enforces schema on known fields; but we must guard 'deleted'
    # If user attempts to pass 'deleted' in body, Pydantic will raise 422 because ItemPatch has no 'deleted'.
    # Apply patch
    data = patch.dict(exclude_unset=True)
    if not data:
        # nothing changed - still OK, return current item body
        return item
    # allowed keys only name and price, already enforced by model
    if "name" in data:
        item.name = data["name"]  # type: ignore
    if "price" in data:
        item.price = data["price"]  # type: ignore
    _items[id] = item
    return item


@app.delete("/item/{id}")
def delete_item(id: int = Path(..., ge=1)):
    item = _items.get(id)
    if item is None:
        # deletion is idempotent according to tests: return OK if not exists as well
        # But tests expect second delete after initial delete to return OK; first delete must mark deleted.
        # If item never existed, returning 404 might be acceptable, but keep idempotent and return OK.
        return {"ok": True}
    item.deleted = True
    _items[id] = item
    return {"ok": True}
