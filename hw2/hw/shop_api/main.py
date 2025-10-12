from fastapi import FastAPI, Query, Depends
from http import HTTPStatus
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException

app = FastAPI(title="Shop API")

class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)

    class Config:
        extra = "forbid"

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(self, **data):
        if 'deleted' in data:
            raise ValueError("Cannot update 'deleted' field")
        super().__init__(**data)

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

items_storage: Dict[int, Item] = {}
carts_storage: Dict[int, Cart] = {}
next_item_id = 1
next_cart_id = 1

@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(item_data: ItemCreate) -> Item:
    global next_item_id
    new_item = Item(
        id=next_item_id,
        name=item_data.name,
        price=item_data.price,
        deleted=False
    )
    items_storage[next_item_id] = new_item
    next_item_id += 1
    return new_item

@app.get("/item/{item_id}")
def get_item(item_id: int) -> Item:
    if item_id not in items_storage or items_storage[item_id].deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return items_storage[item_id]

@app.get("/item")
def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False
) -> List[Item]:
    filtered_items = []

    for item in items_storage.values():
        if not show_deleted and item.deleted:
            continue
        if min_price is not None and item.price < min_price:
            continue
        if max_price is not None and item.price > max_price:
            continue
        filtered_items.append(item)

    return filtered_items[offset:offset + limit]

@app.put("/item/{item_id}")
def update_item(item_id: int, item_data: ItemCreate) -> Item:
    if item_id not in items_storage:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    item = items_storage[item_id]
    item.name = item_data.name
    item.price = item_data.price
    return item

@app.patch("/item/{item_id}")
def patch_item(item_id: int, item_data: ItemUpdate) -> Item:
    if item_id not in items_storage:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    item = items_storage[item_id]
    if item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)

    if item_data.name is not None:
        item.name = item_data.name
    if item_data.price is not None:
        item.price = item_data.price

    return item

@app.delete("/item/{item_id}")
def delete_item(item_id: int) -> Item:
    if item_id not in items_storage:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    item = items_storage[item_id]
    item.deleted = True
    return item

@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart() -> Dict[str, int]:
    global next_cart_id
    new_cart = Cart(
        id=next_cart_id,
        items=[],
        price=0.0
    )
    carts_storage[next_cart_id] = new_cart
    cart_id = next_cart_id
    next_cart_id += 1

    response = JSONResponse(
        content={"id": cart_id},
        status_code=HTTPStatus.CREATED,
        headers={"location": f"/cart/{cart_id}"}
    )
    return response

@app.get("/cart/{cart_id}")
def get_cart(cart_id: int) -> Cart:
    if cart_id not in carts_storage:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    cart = carts_storage[cart_id]
    total_price = 0.0

    for cart_item in cart.items:
        if cart_item.id in items_storage and not items_storage[cart_item.id].deleted:
            total_price += items_storage[cart_item.id].price * cart_item.quantity

    cart.price = total_price
    return cart

@app.get("/cart")
def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
) -> List[Cart]:
    filtered_carts = []

    for cart in carts_storage.values():
        total_price = 0.0
        total_quantity = 0

        for cart_item in cart.items:
            if cart_item.id in items_storage and not items_storage[cart_item.id].deleted:
                total_price += items_storage[cart_item.id].price * cart_item.quantity
            total_quantity += cart_item.quantity

        cart.price = total_price

        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        filtered_carts.append(cart)

    return filtered_carts[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int) -> Cart:
    if cart_id not in carts_storage:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    if item_id not in items_storage:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    cart = carts_storage[cart_id]
    item = items_storage[item_id]

    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            break
    else:
        new_cart_item = CartItem(
            id=item_id,
            name=item.name,
            quantity=1,
            available=not item.deleted
        )
        cart.items.append(new_cart_item)

    total_price = 0.0
    for cart_item in cart.items:
        if cart_item.id in items_storage and not items_storage[cart_item.id].deleted:
            total_price += items_storage[cart_item.id].price * cart_item.quantity

    cart.price = total_price
    return cart
