from fastapi import FastAPI, HTTPException, Query, Path, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from typing import List, Optional


app = FastAPI(title="Shop API")


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    price: float

class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    price: Optional[float] = None

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float


items: dict[int, dict] = {}
carts: dict[int, dict] = {}
item_id_counter = 0
cart_id_counter = 0

# Эндпоинты для Cart

@app.post("/cart")
async def create_cart():
    global cart_id_counter
    cart_id_counter += 1
    new_id = cart_id_counter
    carts[new_id] = {
        "id": new_id,
        "items": [],
        "price": 0.0
    }
    return JSONResponse(
        status_code=201,
        content={"id": new_id},
        headers={"Location": f"/cart/{new_id}"}
    )

@app.get("/cart/{cart_id}", response_model=Cart)
async def get_cart(cart_id: int = Path(..., ge=1)):
    if cart_id not in carts:
        raise HTTPException(status_code=404, detail="Cart not found")
    return carts[cart_id]

@app.get("/cart", response_model=List[Cart])
async def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
):
    all_carts = list(carts.values())
    filtered = []
    for cart in all_carts:
        total_price = cart["price"]
        total_quantity = sum(item["quantity"] for item in cart["items"])
        if (
            (min_price is None or total_price >= min_price) and
            (max_price is None or total_price <= max_price) and
            (min_quantity is None or total_quantity >= min_quantity) and
            (max_quantity is None or total_quantity <= max_quantity)
        ):
            filtered.append(cart)
    return filtered[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
async def add_to_cart(cart_id: int = Path(..., ge=1), item_id: int = Path(..., ge=1)):
    if cart_id not in carts:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    
    cart = carts[cart_id]
    item = items[item_id]
    
    existing_item = next((ci for ci in cart["items"] if ci["id"] == item_id), None)
    if existing_item:
        existing_item["quantity"] += 1
    else:
        cart["items"].append({
            "id": item_id,
            "name": item["name"],
            "quantity": 1,
            "available": not item["deleted"]
        })
    
    cart["price"] = sum(
        ci["quantity"] * items[ci["id"]]["price"]
        for ci in cart["items"] if ci["available"]
    )
    return cart

# Эндпоинты для Item

@app.post("/item")
async def create_item(item: ItemCreate):
    global item_id_counter
    item_id_counter += 1
    new_id = item_id_counter
    items[new_id] = {
        "id": new_id,
        "name": item.name,
        "price": item.price,
        "deleted": False
    }
    return JSONResponse(
        status_code=201,
        content=items[new_id],
        headers={"Location": f"/item/{new_id}"}
    )

@app.get("/item/{item_id}", response_model=Item)
async def get_item(item_id: int = Path(..., ge=1)):
    if item_id not in items or items[item_id]["deleted"]:
        raise HTTPException(status_code=404, detail="Item not found")
    return items[item_id]

@app.get("/item", response_model=List[Item])
async def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False)
):
    all_items = list(items.values())
    filtered = []
    for itm in all_items:
        if not show_deleted and itm["deleted"]:
            continue
        if (
            (min_price is None or itm["price"] >= min_price) and
            (max_price is None or itm["price"] <= max_price)
        ):
            filtered.append(itm)
    return filtered[offset:offset + limit]

@app.put("/item/{item_id}", response_model=Item)
async def update_item(item: ItemCreate, item_id: int = Path(..., ge=1)):
    if item_id not in items or items[item_id]["deleted"]:
        raise HTTPException(status_code=404, detail="Item not found")
    items[item_id]["name"] = item.name
    items[item_id]["price"] = item.price
    # обновление корзины
    for cart in carts.values():
        for ci in cart["items"]:
            if ci["id"] == item_id:
                ci["name"] = item.name
        cart["price"] = sum(
            ci["quantity"] * items[ci["id"]]["price"]
            for ci in cart["items"] if ci["available"]
        )
    return items[item_id]

@app.patch("/item/{item_id}", response_model=Item)
async def partial_update_item(update: ItemUpdate, item_id: int = Path(..., ge=1)):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    if items[item_id]["deleted"]:
        raise HTTPException(status_code=304)
    if update.name is not None:
        items[item_id]["name"] = update.name
    if update.price is not None:
        items[item_id]["price"] = update.price
    # обновление корзины
    for cart in carts.values():
        for ci in cart["items"]:
            if ci["id"] == item_id:
                if update.name is not None:
                    ci["name"] = update.name
        if update.price is not None:
            cart["price"] = sum(
                ci["quantity"] * items[ci["id"]]["price"]
                for ci in cart["items"] if ci["available"]
            )
    return items[item_id]

@app.delete("/item/{item_id}")
async def delete_item(item_id: int = Path(..., ge=1)):
    if item_id not in items:
        raise HTTPException(status_code=404, detail="Item not found")
    items[item_id]["deleted"] = True
    # обновление корзины
    for cart in carts.values():
        for ci in cart["items"]:
            if ci["id"] == item_id:
                ci["available"] = False
        cart["price"] = sum(
            ci["quantity"] * items[ci["id"]]["price"]
            for ci in cart["items"] if ci["available"]
        )
    return Response(status_code=200)
