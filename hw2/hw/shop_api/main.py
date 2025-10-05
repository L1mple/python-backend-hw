from http import HTTPStatus
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, ConfigDict
from starlette import status

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
    items: List[ItemInCart]
    price: float = 0

class ItemCreation(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)

class ItemUpdate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., ge=0)
    deleted: Optional[bool] = False

class ItemPatch(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, ge=0)
    model_config = ConfigDict(extra='forbid')


db_carts = {}
db_items = {}
quantities = {}
carts_counter = 0
items_counter = 0


def get_new_item_id():
    global items_counter
    items_counter += 1
    return items_counter

def get_new_card_id():
    global carts_counter
    carts_counter += 1
    return carts_counter

def update_carts():
    for cart in db_carts.values():
        quantity = 0
        price = 0
        for item_in_cart in cart.items:
            item = db_items[item_in_cart.id]
            if item.deleted:
                item_in_cart.available = False
            else:
                quantity += item_in_cart.quantity
                price += item.price * item_in_cart.quantity
        cart.price = price
        quantities[cart.id] = quantity



@app.post("/item", status_code=status.HTTP_201_CREATED)
async def create_item(params: ItemCreation):
    new_item_id = get_new_item_id()
    new_item = Item(
        id=new_item_id,
        name=params.name,
        price=params.price
    )
    db_items[new_item_id] = new_item
    return new_item

@app.get("/item/{id}")
async def get_item(id: int):
    if id not in db_items or db_items[id].deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_items[id]

@app.get("/item")
async def get_items_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
):
    items = list(db_items.values())

    if not show_deleted:
        items = [i for i in items if not i.deleted]
    if min_price is not None:
        items = [i for i in items if i.price >= min_price]
    if max_price is not None:
        items = [i for i in items if i.price <= max_price]

    return items[offset: offset + limit]

@app.put("/item/{id}", response_model=Item)
async def update_item(id: int, params: ItemUpdate):
    if id not in db_items:
        raise HTTPException(status_code=404, detail="Item not found")
    updated = db_items[id].model_copy(update={"id": id, **params.model_dump()})
    db_items[id] = updated
    update_carts()
    return updated

@app.patch("/item/{id}", response_model=Item)
async def patch_item(id: int, params: ItemPatch):
    old = db_items.get(id)
    if old is None:
        raise HTTPException(status_code=404, detail="Item not found")

    if old.deleted:
        return Response(status_code=304)

    patched = old.model_copy(update={"id": id, **params.model_dump(exclude_unset=True)})
    db_items[id] = patched
    update_carts()
    return patched


@app.delete("/item/{id}")
async def delete_item(id: int):
    if id not in db_items:
        return
    db_items[id].deleted = True
    update_carts()
    return


@app.post("/cart", status_code=HTTPStatus.CREATED)
async def create_cart(response: Response):
    new_cart_id = get_new_card_id()
    new_cart = Cart(id=new_cart_id, items=[])
    db_carts[new_cart_id] = new_cart
    quantities[new_cart_id] = 0
    response.headers["Location"] = f"/cart/{new_cart_id}"
    return {"id": new_cart_id}


@app.get("/cart/{id}")
async def get_cart(id: int):
    if id not in db_carts:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_carts[id]


@app.get("/cart")
async def get_carts_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
):
    carts = list(db_carts.values())
    if min_price is not None:
        carts = [cart for cart in carts if cart.price >= min_price]
    if max_price is not None:
        carts = [cart for cart in carts if cart.price <= max_price]
    if min_quantity is not None:
        carts = [cart for cart in carts if quantities[cart.id] >= min_quantity]
    if max_quantity is not None:
        carts = [cart for cart in carts if quantities[cart.id] <= max_quantity]
    return carts[offset: offset + limit]


@app.post("/cart/{card_id}/add/{item_id}")
async def add_item_to_cart(
    card_id: int,
    item_id: int,
):
    if card_id not in db_carts:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in db_items:
        raise HTTPException(status_code=404, detail="Item not found")
    item = db_items[item_id]
    for item_in_card in db_carts[card_id].items:
        if item_in_card.id == item_id:
            item_in_card.quantity += 1
            break
    else:
        item_in_cart = ItemInCart(
            id=item_id,
            name=item.name,
            quantity=1,
            available=item.deleted
        )
        db_carts[card_id].items.append(item_in_cart)
    update_carts()


















