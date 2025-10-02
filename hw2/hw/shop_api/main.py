from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional, Dict
from http import HTTPStatus
from typing_extensions import Annotated

app = FastAPI(title="Shop API")


# ------------------ MODELS ------------------ #
class ItemBase(BaseModel):
    name: str
    price: float


class ItemCreate(ItemBase):
    pass


class Item(ItemBase):
    id: int
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


# ------------------ STORAGE ------------------ #
items: Dict[int, Item] = {}
carts: Dict[int, Cart] = {}
item_counter = 1
cart_counter = 1


# ------------------ ITEM ENDPOINTS ------------------ #
@app.post("/item", response_model=Item, status_code=HTTPStatus.CREATED)
def create_item(item: ItemCreate):
    global item_counter
    new_item = Item(id=item_counter, name=item.name, price=item.price, deleted=False)
    items[item_counter] = new_item
    item_counter += 1
    return new_item


@app.get("/item/{item_id}", response_model=Item)
def get_item(item_id: int):
    item = items.get(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@app.get("/item", response_model=List[Item])
def list_items(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Optional[Annotated[float, Query(ge=0.0)]] = None,
    max_price: Optional[Annotated[float, Query(ge=0.0)]] = None,
    show_deleted: bool = False,
):
    filtered = list(items.values())

    if not show_deleted:
        filtered = [i for i in filtered if not i.deleted]

    if min_price is not None:
        filtered = [i for i in filtered if i.price >= min_price]

    if max_price is not None:
        filtered = [i for i in filtered if i.price <= max_price]

    return filtered[offset: offset + limit]


@app.put("/item/{item_id}", response_model=Item)
def update_item(item_id: int, new_item: ItemCreate):
    item = items.get(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    item.name = new_item.name
    item.price = new_item.price
    items[item_id] = item
    return item


@app.patch("/item/{item_id}", response_model=Item)
async def patch_item(item_id: int, request: Request):
    item = items.get(item_id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    if item.deleted:
        return Response(status_code=HTTPStatus.NOT_MODIFIED)

    body = await request.json()

    allowed_fields = {"name", "price"}
    for key in body:
        if key not in allowed_fields:
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail=f"Cannot modify '{key}'"
            )
        if key == "deleted":
            raise HTTPException(
                status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
                detail="Cannot modify 'deleted'"
            )

    if "name" in body:
        item.name = body["name"]
    if "price" in body:
        item.price = body["price"]

    items[item_id] = item
    return item


@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    item = items.get(item_id)
    if not item:
        return {"status": "already deleted"}

    item.deleted = True
    items[item_id] = item
    return {"status": "deleted"}


# ------------------ CART ENDPOINTS ------------------ #
@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart():
    global cart_counter
    cart = Cart(id=cart_counter, items=[], price=0.0)
    carts[cart_counter] = cart

    response = JSONResponse(
        content={"id": cart_counter},
        status_code=HTTPStatus.CREATED,
        headers={"Location": f"/cart/{cart_counter}"} 
    )
    cart_counter += 1
    return response


@app.get("/cart/{cart_id}", response_model=Cart)
def get_cart(cart_id: int):
    cart = carts.get(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return cart


@app.get("/cart", response_model=List[Cart])
def list_carts(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Optional[Annotated[float, Query(ge=0.0)]] = None,
    max_price: Optional[Annotated[float, Query(ge=0.0)]] = None,
    min_quantity: Optional[Annotated[int, Query(ge=0)]] = None,
    max_quantity: Optional[Annotated[int, Query(ge=0)]] = None,
):
    filtered = list(carts.values())

    if min_price is not None:
        filtered = [c for c in filtered if c.price >= min_price]
    if max_price is not None:
        filtered = [c for c in filtered if c.price <= max_price]

    if min_quantity is not None:
        filtered = [c for c in filtered if sum(i.quantity for i in c.items) >= min_quantity]
    if max_quantity is not None:
        filtered = [c for c in filtered if sum(i.quantity for i in c.items) <= max_quantity]

    return filtered[offset: offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
def add_item_to_cart(cart_id: int, item_id: int):
    cart = carts.get(cart_id)
    item = items.get(item_id)

    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    for cart_item in cart.items:
        if cart_item.id == item_id:
            cart_item.quantity += 1
            break
    else:
        cart.items.append(CartItem(id=item.id, name=item.name, quantity=1, available=not item.deleted))

    cart.price = sum(i.quantity * items[i.id].price for i in cart.items if not items[i.id].deleted)
    carts[cart_id] = cart
    return cart
