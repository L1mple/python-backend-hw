from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from typing import List, Optional, Dict, Any
from fastapi.responses import JSONResponse, Response
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

class ItemBase(BaseModel):
    name: str
    price: float

class Item(ItemBase):
    id: int
    deleted: bool = False

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    model_config = ConfigDict(extra="forbid")

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool = True

class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float

items: Dict[int, Item] = {}
carts: Dict[int, Dict[str, Any]] = {}

item_counter = 1
cart_counter = 1

def get_item(item_id: int) -> Item:
    if item_id not in items or items[item_id].deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]

def get_cart(cart_id: int) -> Dict[str, Any]:
    if cart_id not in carts:
        raise HTTPException(status_code=404, detail="Cart not found")
    return carts[cart_id]

def get_item_in_cart(cart, item_id: int):
    for i, cart_item in enumerate(cart['items']):
        if cart_item['id'] == item_id:
            return i, cart_item
    return None, None

def calculate_cart_price(cart):
    total = 0.0
    for cart_item in cart['items']:
        if cart_item['available']:
            item = items.get(cart_item["id"])
            if item and not item.deleted:
                total += cart_item['quantity'] * item.price
    return total

def update_cart_items_availability(cart):
    for cart_item in cart['items']:
        item = items.get(cart_item["id"])
        cart_item['available'] = bool(item and not item.deleted)\
        
@app.post("/item", response_model=Item, status_code=201)
def create_item(data: ItemBase):
    global item_counter
    _id = item_counter
    item_counter += 1
    new_item = Item(id=_id, name=data.name, price=data.price, deleted=False)
    items[_id] = new_item
    return new_item

@app.get("/item/{id}", response_model=Item)
def get_item_endpoint(id: int):
    return get_item(id)

@app.get("/item", response_model=List[Item])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False)
):
    result = list(items.values())
    if not show_deleted:
        result = [it for it in result if not it.deleted]
    if min_price is not None:
        result = [it for it in result if it.price >= min_price]
    if max_price is not None:
        result = [it for it in result if it.price <= max_price]
    return result[offset:offset + limit]

@app.put("/item/{id}", response_model=Item)
def update_item(id: int, data: ItemBase):
    if id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    items[id].name = data.name
    items[id].price = data.price
    return items[id]

@app.patch("/item/{id}", response_model=Item)
def patch_item(id: int, patch: ItemPatch):
    if id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    item = items[id]
    if item.deleted:
        return Response(status_code=304)
    if patch.name is not None:
        item.name = patch.name
    if patch.price is not None:
        item.price = patch.price
    return item

@app.delete("/item/{id}")
def delete_item(id: int):
    if id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    items[id].deleted = True

    for cart in carts.values():
        update_cart_items_availability(cart)
        cart["price"] = calculate_cart_price(cart)
    return {"detail": "Item marked as deleted"}

@app.post("/cart", status_code=201)
def create_cart():
    global cart_counter
    cart_id = cart_counter
    cart_counter += 1
    carts[cart_id] = {"id": cart_id, "items": [], "price": 0.0}
    headers = {"Location": f"/cart/{cart_id}"}
    return JSONResponse(content={"id": cart_id}, status_code=201, headers=headers)

@app.get("/cart/{id}", response_model=Cart)
def get_cart_endpoint(id: int):
    cart = get_cart(id)
    update_cart_items_availability(cart)
    cart["price"] = calculate_cart_price(cart)
    return Cart(
        id=cart["id"],
        items=[CartItem(**i) for i in cart['items']],
        price=cart["price"]
    )

@app.get("/cart", response_model=List[Cart])
def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
):
    res = []
    for cart in carts.values():
        update_cart_items_availability(cart)
        cart["price"] = calculate_cart_price(cart)
        total_q = sum(i['quantity'] for i in cart['items'])
        if min_price is not None and cart["price"] < min_price:
            continue
        if max_price is not None and cart["price"] > max_price:
            continue
        if min_quantity is not None and total_q < min_quantity:
            continue
        if max_quantity is not None and total_q > max_quantity:
            continue
        res.append(Cart(
            id=cart["id"],
            items=[CartItem(**i) for i in cart['items']],
            price=cart["price"]))

    return res[offset:offset+limit]

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    cart = get_cart(cart_id)
    item = get_item(item_id)
    idx, cart_item = get_item_in_cart(cart, item_id)
    if cart_item:
        cart_item["quantity"] += 1
    else:
        cart['items'].append({
            "id": item.id,
            "name": item.name,
            "quantity": 1,
            "available": not item.deleted
        })

    update_cart_items_availability(cart)
    cart["price"] = calculate_cart_price(cart)

    return {"detail": "Item added to cart", "cart_id": cart_id}

print("App started. Routes registered:", app.routes)
