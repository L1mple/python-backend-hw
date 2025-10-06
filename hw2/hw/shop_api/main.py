from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi import Request

app = FastAPI(title="Shop API")

items_db = {}
carts_db = {}
cart_counter = 0
item_counter = 0

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float

class ItemCreate(BaseModel):
    name: str
    price: float

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    class Config:
        extra = "forbid"

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.post("/item", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    global item_counter
    item_counter += 1
    new_item = Item(id=item_counter, name=item.name, price=item.price, deleted=False)
    items_db[item_counter] = new_item
    return new_item

@app.get("/item/{id}", response_model=Item)
async def get_item(id: int):
    item = items_db.get(id)
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.get("/item")
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False
):
    filtered_items = list(items_db.values())
    if not show_deleted:
        filtered_items = [item for item in filtered_items if not item.deleted]
    if min_price is not None:
        filtered_items = [item for item in filtered_items if item.price >= min_price]
    if max_price is not None:
        filtered_items = [item for item in filtered_items if item.price <= max_price]
    return filtered_items[offset:offset + limit]

@app.put("/item/{id}", response_model=Item)
async def update_item(id: int, item: ItemCreate):
    if id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    updated_item = Item(id=id, name=item.name, price=item.price, deleted=items_db[id].deleted)
    items_db[id] = updated_item
    return updated_item

@app.patch("/item/{id}", response_model=Item)
async def partial_update_item(id: int, item: ItemUpdate):
    if id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    stored_item = items_db[id]
    if stored_item.deleted:
        raise HTTPException(status_code=304, detail="Item is deleted")
    try:
        update_data = item.model_dump(exclude_unset=True)
        updated_item = stored_item.model_copy(update=update_data)
        items_db[id] = updated_item
        return updated_item
    except ValidationError as e:
        raise HTTPException(status_code=422, detail="Invalid fields in request")

@app.delete("/item/{id}", response_model=dict)
async def delete_item(id: int):
    if id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db[id].deleted = True
    return {"status": "success"}

@app.post("/cart", response_model=dict, status_code=201)
async def create_cart():
    global cart_counter
    cart_counter += 1
    carts_db[cart_counter] = Cart(id=cart_counter, items=[], price=0.0)
    return JSONResponse(
        content={"id": cart_counter},
        headers={"Location": f"/cart/{cart_counter}"},
        status_code=201
    )

@app.get("/cart/{id}", response_model=Cart)
async def get_cart(id: int):
    cart = carts_db.get(id)
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart

@app.get("/cart")
async def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
):
    filtered_carts = list(carts_db.values())
    if min_price is not None:
        filtered_carts = [cart for cart in filtered_carts if cart.price >= min_price]
    if max_price is not None:
        filtered_carts = [cart for cart in filtered_carts if cart.price <= max_price]
    if min_quantity is not None:
        filtered_carts = [cart for cart in filtered_carts if sum(item.quantity for item in cart.items) >= min_quantity]
    if max_quantity is not None:
        filtered_carts = [cart for cart in filtered_carts if sum(item.quantity for item in cart.items) <= max_quantity]
    return filtered_carts[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in items_db:
        raise HTTPException(status_code=404, detail="Item not found")

    cart = carts_db[cart_id]
    item = items_db[item_id]

    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            cart.price += item.price
            return {"status": "success"}

    cart_item = CartItem(
        id=item.id,
        name=item.name,
        quantity=1,
        available=not item.deleted
    )
    cart.items.append(cart_item)
    cart.price += item.price
    return {"status": "success"}
