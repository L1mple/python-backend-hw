from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, confloat, conint, PositiveInt
from typing import Dict, List, Optional

app = FastAPI()

# ---------- MODELS ----------

class ItemBase(BaseModel):
    name: str
    price: confloat(ge=0.0)

    class Config:
        extra = 'forbid'  # запрет лишних полей во всех моделях


class ItemCreate(ItemBase):
    pass


class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[confloat(ge=0.0)] = None

    class Config:
        extra = 'forbid'  # PATCH должен возвращать 422 при любых неожиданных полях


class Item(ItemBase):
    id: int
    deleted: bool = False


class CartItemOut(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class CartOut(BaseModel):
    id: int
    items: List[CartItemOut]
    price: float


# ---------- IN-MEMORY "БАЗА" ----------

_next_item_id = 1
_items: Dict[int, Item] = {}

_next_cart_id = 1
_carts: Dict[int, Dict[int, int]] = {}


# ---------- ITEM ENDPOINTS ----------

@app.post('/item', response_model=Item, status_code=201)
def create_item(item_in: ItemCreate):
    global _next_item_id
    item = Item(id=_next_item_id, name=item_in.name, price=item_in.price, deleted=False)
    _items[_next_item_id] = item
    _next_item_id += 1
    return item


@app.get('/item/{id}', response_model=Item)
def get_item(id: int):
    item = _items.get(id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404)
    return item


@app.get('/item', response_model=List[Item])
def list_items(
    offset: conint(ge=0) = 0,
    limit: PositiveInt = 10,
    min_price: Optional[confloat(ge=0.0)] = None,
    max_price: Optional[confloat(ge=0.0)] = None,
    show_deleted: bool = False
):
    items = [
        item for item in _items.values()
        if (show_deleted or not item.deleted)
        and (min_price is None or item.price >= min_price)
        and (max_price is None or item.price <= max_price)
    ]
    return sorted(items, key=lambda x: x.id)[offset:offset + limit]


@app.put('/item/{id}', response_model=Item)
def replace_item(id: int, item_in: ItemCreate):
    if id not in _items:
        raise HTTPException(status_code=404)
    old_item = _items[id]
    new_item = Item(id=id, name=item_in.name, price=item_in.price, deleted=old_item.deleted)
    _items[id] = new_item
    return new_item


@app.patch('/item/{id}', response_model=Item)
def patch_item(id: int, patch: ItemPatch):
    item = _items.get(id)
    if item is None:
        raise HTTPException(status_code=404)
    if item.deleted:
        return JSONResponse(status_code=304, content=item.model_dump())

    data = patch.dict(exclude_unset=True)
    if not data:
        return item

    if 'name' in data:
        item.name = data['name']
    if 'price' in data:
        item.price = data['price']

    _items[id] = item
    return item


@app.delete('/item/{id}')
def delete_item(id: int):
    item = _items.get(id)
    if item is None:
        return {'ok': True}
    item.deleted = True
    _items[id] = item
    return {'ok': True}


# ---------- CART ENDPOINTS ----------

@app.post('/cart')
def create_cart():
    global _next_cart_id
    cid = _next_cart_id
    _next_cart_id += 1
    _carts[cid] = {}
    response = JSONResponse(status_code=201, content={'id': cid})
    response.headers['Location'] = f'/cart/{cid}'
    return response


@app.post('/cart/{cart_id}/add/{item_id}')
def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in _carts:
        raise HTTPException(status_code=404)
    if item_id not in _items:
        raise HTTPException(status_code=404)

    item_map = _carts[cart_id]
    item_map[item_id] = item_map.get(item_id, 0) + 1
    return {'ok': True}


def _cart_to_response(cart_id: int) -> CartOut:
    item_map = _carts.get(cart_id, {})
    items_out = []
    total_price = 0.0

    for iid, qty in item_map.items():
        item = _items.get(iid)
        available = item is not None and not item.deleted
        name = item.name if item else ''
        if available:
            total_price += item.price * qty
        items_out.append(CartItemOut(id=iid, name=name, quantity=qty, available=available))

    return CartOut(id=cart_id, items=items_out, price=total_price)


@app.get('/cart/{id}', response_model=CartOut)
def get_cart(id: int):
    if id not in _carts:
        raise HTTPException(status_code=404)
    return _cart_to_response(id)


@app.get('/cart', response_model=List[CartOut])
def list_carts(
    offset: conint(ge=0) = 0,
    limit: PositiveInt = 10,
    min_price: Optional[confloat(ge=0.0)] = None,
    max_price: Optional[confloat(ge=0.0)] = None,
    min_quantity: Optional[conint(ge=0)] = None,
    max_quantity: Optional[conint(ge=0)] = None,
):
    carts_out = []
    for cid in sorted(_carts.keys()):
        cart_resp = _cart_to_response(cid)
        total_quantity = sum(i.quantity for i in cart_resp.items)
        if (
            (min_price is None or cart_resp.price >= min_price)
            and (max_price is None or cart_resp.price <= max_price)
            and (min_quantity is None or total_quantity >= min_quantity)
            and (max_quantity is None or total_quantity <= max_quantity)
        ):
            carts_out.append(cart_resp)
    return carts_out[offset:offset + limit]
