from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional
from http import HTTPStatus

app = FastAPI(title="Shop API")

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

class ItemInCart(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: List[ItemInCart] = []
    price: float

class ItemCreatingObj(BaseModel):
    name: str
    price: float = Field(..., gt=0)

class ItemUpdatingObj(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    model_config = ConfigDict(extra="forbid")

items_dict = {}
carts_dict = {}
item_id_counter = 0
cart_id_counter = 0

@app.post("/cart", response_model=dict, status_code=HTTPStatus.CREATED)
async def create_cart(response: Response):
    global cart_id_counter
    cart_id_counter += 1
    carts_dict[cart_id_counter] = {"id": cart_id_counter, "items": [], "price": 0.0}
    response.headers["location"] = f"/cart/{cart_id_counter}"
    return {"id": cart_id_counter}

@app.get("/cart/{id}", response_model=Cart)
async def get_cart(id: int):
    if id not in carts_dict:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return carts_dict[id]

@app.get("/cart", response_model=List[Cart])
async def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
):
    carts = list(carts_dict.values())
    if min_price is not None:
        carts = [cart for cart in carts if cart["price"] >= min_price]
    if max_price is not None:
        carts = [cart for cart in carts if cart["price"] <= max_price]
    if min_quantity is not None:
        carts = [cart for cart in carts if sum(item["quantity"] for item in cart["items"]) >= min_quantity]
    if max_quantity is not None:
        carts = [cart for cart in carts if sum(item["quantity"] for item in cart["items"]) <= max_quantity]
    return carts[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
async def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_dict:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    if item_id not in items_dict or items_dict[item_id]["deleted"]:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    cart = carts_dict[cart_id]
    for cart_item in cart["items"]:
        if cart_item["id"] == item_id:
            cart_item["quantity"] += 1
            cart["price"] += items_dict[item_id]["price"]
            return cart

    cart["items"].append({
        "id": item_id,
        "name": items_dict[item_id]["name"],
        "quantity": 1,
        "available": True
    })
    cart["price"] += items_dict[item_id]["price"]
    return cart

@app.post("/item", response_model=Item, status_code=HTTPStatus.CREATED)
async def create_item(item: ItemCreatingObj):
    global item_id_counter
    item_id_counter += 1
    items_dict[item_id_counter] = {
        "id": item_id_counter,
        "name": item.name,
        "price": item.price,
        "deleted": False
    }
    return items_dict[item_id_counter]

@app.get("/item/{id}", response_model=Item)
async def get_item(id: int):
    if id not in items_dict or items_dict[id]["deleted"]:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return items_dict[id]

@app.get("/item", response_model=List[Item])
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False
):
    items = [item for item in items_dict.values() if show_deleted or not item["deleted"]]
    if min_price is not None:
        items = [item for item in items if item["price"] >= min_price]
    if max_price is not None:
        items = [item for item in items if item["price"] <= max_price]
    return items[offset:offset + limit]

@app.put("/item/{id}", response_model=Item)
async def update_item(id: int, item: ItemCreatingObj):
    if id not in items_dict:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    items_dict[id].update({
        "name": item.name,
        "price": item.price,
        "deleted": items_dict[id]["deleted"]
    })
    return items_dict[id]

@app.patch("/item/{id}", response_model=Item)
async def partial_update_item(id: int, item: ItemUpdatingObj):
    if id not in items_dict:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    if items_dict[id]["deleted"]:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED, detail="Item is deleted")
    if item.name is not None:
        items_dict[id]["name"] = item.name
    if item.price is not None:
        items_dict[id]["price"] = item.price
    return items_dict[id]

@app.delete("/item/{id}", response_model=dict)
async def delete_item(id: int):
    if id not in items_dict:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    items_dict[id]["deleted"] = True
    for cart in carts_dict.values():
        for cart_item in cart["items"]:
            if cart_item["id"] == id:
                cart_item["available"] = False
                cart["price"] -= cart_item["quantity"] * items_dict[id]["price"]
    return {"status_code": HTTPStatus.OK}