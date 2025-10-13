from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, ConfigDict

app = FastAPI(title="Shop API")

Instrumentator().instrument(app).expose(app)

class ItemDTO(BaseModel):
    name: str
    price: float

class PatchItemDTO(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    model_config = ConfigDict(extra="forbid")

class PutItemDTO(BaseModel):
    name: str
    price: float
    deleted: Optional[bool] = False


class Item:
    def __init__(self, id: int, name: str, price: float):
        self.id: int = id
        self.name: str = name
        self.deleted: bool = False
        self.price:float = price
    
    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "deleted": self.deleted,
            "price": self.price
        }
    
    def delete(self):
        self.deleted = True


class CartItem:
    def __init__(self, item: Item, quantity: int):
        self.id: int = item.id
        self.name: str = item.name
        self.quantity: int = quantity
        self.available: bool = not item.deleted
        self.price: float = item.price
    
    def add(self, quantity: int = 1):
        self.quantity += quantity
    
    def get_total_price(self):
        return self.price * self.quantity

    def to_json(self):
        return {
            "id": self.id,
            "name": self.name,
            "quantity": self.quantity,
            "available": self.available
        }

class Cart:
    def __init__(self, id: int):
        self.id: int = id
        self.items: Dict[int, CartItem] = {}

    def add_item(self, item: Item, quantity: int = 1):
        if item.id in self.items:
            self.items[item.id].add(quantity)
        else:
            self.items[item.id] = CartItem(item, quantity)
    
    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.values())
    
    def get_all_quantity(self):
        return sum(item.quantity for item in self.items.values())

    def to_json(self):
        return {
            "id": self.id,
            "items": [item.to_json() for item in self.items.values()],
            "price": self.get_total_price()
        }



carts: Dict[int, Cart] = {}
items: Dict[int, Item] = {}


@app.post("/cart", status_code=201)
async def create_cart():
    cart = Cart(id=len(carts) + 1)
    carts[cart.id] = cart
    return JSONResponse(
        status_code=201,
        content={"id": cart.id},
        headers={"Location": f"/cart/{cart.id}"}
    )


@app.get("/cart/{id}")
async def get_cart(id: int):
    cart = carts.get(id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    return JSONResponse(
        status_code=200,
        content=cart.to_json(),
        headers={"Location": f"/cart/{cart.id}"}
    )

@app.get("/cart")
async def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    filtered = filter(
        lambda cart: (min_price is None or cart.get_total_price() >= min_price) and
                     (max_price is None or cart.get_total_price() <= max_price) and
                     (min_quantity is None or cart.get_all_quantity() >= min_quantity) and
                     (max_quantity is None or cart.get_all_quantity() <= max_quantity),
        carts.values()
    )
    result = list(filtered)[offset:offset + limit]
    return [cart.to_json() for cart in result]


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int):
    cart = carts.get(cart_id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    item = items.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    cart.add_item(item)
    return {"message": "Item added to cart"}


@app.post("/item", status_code=201)
async def create_item(item_dto: ItemDTO):
    item = Item(id=len(items) + 1, name=item_dto.name, price=item_dto.price)
    items[item.id] = item
    return JSONResponse(
        status_code=201,
        content=item.to_json(),
        headers={"Location": f"/item/{item.id}"}
    )


@app.get("/item/{id}")
async def get_item(id: int):
    item = items.get(id)
    if item is None or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return JSONResponse(
        status_code=200,
        content=item.to_json(),
        headers={"Location": f"/item/{item.id}"}
    )


@app.get("/item")
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
):
    filtered = filter(
        lambda item: (min_price is None or item.price >= min_price) and
                     (max_price is None or item.price <= max_price) and
                     (show_deleted or not item.deleted),
        items.values()
    )
    result = list(filtered)[offset:offset + limit]
    return  [item.to_json() for item in result]


@app.put("/item/{id}")
async def recreate_item(id: int, item_dto: PutItemDTO):
    item = items.get(id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.name = item_dto.name
    item.price = item_dto.price
    item.deleted = item_dto.deleted or False
    
    return JSONResponse(
        status_code=200,
        content=item.to_json(),
        headers={"Location": f"/item/{item.id}"}
    )


@app.patch("/item/{id}")
async def update_item(id: int, item_dto: PatchItemDTO):
    item = items.get(id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.deleted:
        return JSONResponse(status_code=304, content=item.to_json())
    if item_dto.name is not None:
        item.name = item_dto.name
    if item_dto.price is not None:
        item.price = item_dto.price
    return JSONResponse(
        status_code=200,
        content=item.to_json(),
        headers={"Location": f"/item/{item.id}"}
    )

@app.delete("/item/{id}", status_code=200)
async def delete_item(id: int):
    item = items.get(id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item.delete()
    return {"message": "Item deleted"}
