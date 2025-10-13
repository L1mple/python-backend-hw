from fastapi import FastAPI, Query, HTTPException, Response
from pydantic import BaseModel
from typing import Optional, List

app = FastAPI(title="Shop API")

items_memory = {}

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

class ItemCreate(BaseModel):
    name: str
    price: float

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    
    class Config:
        extra = "forbid"

class ItemPut(BaseModel):
    name: str
    price: float
    deleted: Optional[bool] = None

item_counter = 0

@app.post('/item', status_code=201)
def create_item(item: ItemCreate):
    global item_counter
    new_item = Item(id=item_counter, name=item.name, price=item.price, deleted=False)
    items_memory[item_counter] = new_item
    item_counter += 1
    return new_item

@app.get('/item/{item_id}')
def get_item(item_id:int):
    if item_id not in items_memory:
        raise HTTPException(status_code=404, detail="Item not found")
    if items_memory[item_id].deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return items_memory[item_id]

@app.get('/item')
def get_item_list(
    limit: Optional[int] = Query(default=10, ge=1),
    offset: Optional[int] = Query(default=0, ge=0),
    min_price: Optional[float] = Query(default=None, ge = 0),
    max_price: Optional[float] = Query(default=None, ge = 0),
    show_deleted: Optional[bool] = False
):
    all_items = list(items_memory.values())
    if not show_deleted:
        all_items = [v for v in all_items if not v.deleted]
    if min_price is not None:
        all_items = [v for v in all_items if v.price >= min_price]
    if max_price is not None:
        all_items = [v for v in all_items if v.price <= max_price]
    return all_items[offset:offset+limit]


@app.put('/item/{item_id}')
def put_item(item_id: int, item: ItemPut):
    if item_id not in items_memory:
      raise HTTPException(status_code=404, detail="Item not found")
    if item.deleted is not None:
        items_memory[item_id] = Item(id=item_id, name=item.name, price=item.price, deleted=item.deleted)
    if item.deleted is None:
        items_memory[item_id] = Item(id=item_id, name=item.name, price=item.price, deleted=items_memory[item_id].deleted)
    return items_memory[item_id]

@app.patch('/item/{item_id}')
def patch_item(item_id: int, item: ItemPatch):
    if item_id not in items_memory:
        raise HTTPException(status_code=404, detail="Item not found")
    # Проверяем, не удалён ли товар
    if items_memory[item_id].deleted:
        raise HTTPException(status_code=304, detail="Item is deleted")
    
    if item.price is not None:
        items_memory[item_id].price = item.price
    if item.name is not None:
        items_memory[item_id].name = item.name
    return items_memory[item_id]

@app.delete('/item/{item_id}')
def delete_item(item_id: int):
    if item_id not in items_memory:
      raise HTTPException(status_code=404, detail="Item not found")
    items_memory[item_id].deleted = True
    return 


#  - `PUT /item/{id}` - замена товара по `id` (создание запрещено, только замена существующего)
#  - `PATCH /item/{id}` - частичное обновление товара по `id` (разрешено менять все поля, кроме `deleted`)
#  - `DELETE /item/{id}` - удаление товара по `id` (товар помечается как удаленный)

# --- Cart implementation ---

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: List[CartItem] = []
    price: float = 0.0

carts_memory = {}
cart_counter = 0

@app.post('/cart', status_code=201)
def create_cart(response: Response):
    global cart_counter
    cart = Cart(id=cart_counter, items=[], price=0.0)
    carts_memory[cart_counter] = cart
    cart_counter += 1
    response.headers["location"] = f"/cart/{cart.id}"
    return cart

@app.get('/cart/{cart_id}')
def get_cart(cart_id: int):
    if cart_id not in carts_memory:
        raise HTTPException(status_code=404, detail="Cart not found")
    return carts_memory[cart_id]

@app.get('/cart')
def get_cart_list(
    limit: Optional[int] = Query(default=10, ge=1),
    offset: Optional[int] = Query(default=0, ge=0),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0)
):
    all_carts = list(carts_memory.values())
    
    if min_price is not None:
        all_carts = [cart for cart in all_carts if cart.price >= min_price]
    if max_price is not None:
        all_carts = [cart for cart in all_carts if cart.price <= max_price]
    
    if min_quantity is not None:
        all_carts = [cart for cart in all_carts if sum(item.quantity for item in cart.items) >= min_quantity]
    if max_quantity is not None:
        all_carts = [cart for cart in all_carts if sum(item.quantity for item in cart.items) <= max_quantity]
    
    return all_carts[offset:offset+limit]

@app.post('/cart/{cart_id}/add/{item_id}')
def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_memory:
        raise HTTPException(status_code=404, detail="Cart not found")
    if item_id not in items_memory:
        raise HTTPException(status_code=404, detail="Item not found")
    if items_memory[item_id].deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    
    cart = carts_memory[cart_id]
    item = items_memory[item_id]

    existing_item = None
    for cart_item in cart.items:
        if cart_item.id == item_id:
            existing_item = cart_item
            break
    
    if existing_item:
        existing_item.quantity += 1
    else:
        cart_item = CartItem(
            id=item_id,
            name=item.name,
            quantity=1,
            available=not item.deleted
        )
        cart.items.append(cart_item)
    
    total_price = sum(items_memory[cart_item.id].price * cart_item.quantity for cart_item in cart.items if cart_item.id in items_memory and not items_memory[cart_item.id].deleted)
    cart.price = total_price
    
    return cart
