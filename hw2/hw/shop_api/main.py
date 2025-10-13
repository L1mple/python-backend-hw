from fastapi import FastAPI, Response, Query, HTTPException
from typing import Optional
from pydantic import BaseModel, Field
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

items_storage = {} 
carts_storage = {} 

class Item(BaseModel):
    id: int
    name: str
    price: float = Field(gt=0)
    deleted: bool = False

class ItemForCreateUpd(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemForPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    model_config = {"extra": "forbid"}

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: list[CartItem]
    price: float


#Работа с товарами
#----------------------------------

@app.post("/item", response_model=Item, status_code=201)
def create_item(item: ItemForCreateUpd):
    if items_storage:
        id = max(items_storage.keys()) + 1
    else:
        id = 1
    deleted = False
    items_storage[id] = Item(id=id, name=item.name, price=item.price, deleted=deleted)
    return items_storage[id]

@app.put("/item/{id}", response_model=Item)
def put_item(id: int, item: ItemForCreateUpd):
    if id not in items_storage:
        return {"error": "Item not found"}
    stored_item = items_storage[id]
    stored_item.name = item.name
    stored_item.price = item.price
    items_storage[id] = stored_item
    return stored_item

@app.get("/item", response_model=list[Item])
def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False
):
    all_items = list(items_storage.values())

    filtered_items = [
        item for item in all_items
        if (show_deleted or not item.deleted)
        and (min_price is None or item.price >= min_price)
        and (max_price is None or item.price <= max_price)
    ]
    
    return filtered_items[offset : offset + limit]

@app.get("/item/{id}", response_model=Item)
def get_item_id(id: int):
    if id not in items_storage:
        raise HTTPException(status_code=404)
    item = items_storage[id]
    if item.deleted:
        raise HTTPException(status_code=404)
    return item

@app.delete("/item/{id}", response_model=Item)
def delete_item(id: int):
    if id not in items_storage:
        return {"error": "Item not found"}
    stored_item = items_storage[id]
    stored_item.deleted = True
    return stored_item

@app.patch("/item/{id}", response_model=Item)
def patch_item(id: int, item: ItemForPatch):
    if id not in items_storage:
        raise HTTPException(status_code=404)
    stored_item = items_storage[id]
    if stored_item.deleted:
        return Response(status_code=304)
    if item.name is not None:
        stored_item.name = item.name
    if item.price is not None:
        stored_item.price = item.price
    items_storage[id] = stored_item
    return stored_item


#Работа с корзиной
#----------------------------------

@app.post("/cart", status_code=201)
def post_cart(response: Response):
    if carts_storage:
        id = max(carts_storage.keys()) + 1
    else:
        id = 1
    
    new_cart = {
        "id": id,
        "items": {}
    }
    carts_storage[id] = new_cart
    response.headers["location"] = f"/cart/{id}"
    return {"id": id}

@app.get("/cart", response_model=list[Cart])
def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    all_carts = list(carts_storage.values())
    filtered_carts = []
    
    for cart in all_carts:
        cart_items = []
        total_quantity = 0
        total_price = 0
        
        for item_id, quantity in cart["items"].items():
            item = items_storage.get(item_id)
            if item:
                available = not item.deleted
                cart_items.append({
                    "id": item_id,
                    "name": item.name,
                    "quantity": quantity,
                    "available": available
                })
                if available:
                    total_price += item.price * quantity
                total_quantity += quantity
        
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue

        filtered_carts.append({
            "id": cart["id"],
            "items": cart_items,
            "price": total_price
        })
    
    return filtered_carts[offset : offset + limit]

@app.get("/cart/{id}", response_model=Cart)
def get_cart_id(id: int):
    if id not in carts_storage:
        return {"error": "Cart not found"}
    
    cart = carts_storage[id]
    cart_items = []
    total_price = 0
    
    for item_id, quantity in cart["items"].items():
        item = items_storage.get(item_id)
        if item:
            available = not item.deleted
            cart_items.append(CartItem(
                id=item_id,
                name=item.name,
                quantity=quantity,
                available=available
            ))
            if available:
                total_price += item.price * quantity
    
    return Cart(
        id=cart["id"],
        items=cart_items,
        price=total_price
    )

@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
def add_item_to_cart(cart_id: int, item_id: int): 
    if cart_id not in carts_storage:
        return {"error": "Cart not found"}
    if item_id not in items_storage:
        return {"error": "Item not found"}
    
    cart = carts_storage[cart_id]

    if item_id in cart["items"]:
        cart["items"][item_id] += 1
    else:
        cart["items"][item_id] = 1

    cart_items = []
    total_price = 0
    
    for item_id_in_cart, quantity in cart["items"].items():
        item = items_storage[item_id_in_cart]
        available = not item.deleted
        cart_items.append(CartItem(
            id=item_id_in_cart,
            name=item.name,
            quantity=quantity,
            available=available
        ))
        if available:
            total_price += item.price * quantity
    
    return Cart(
        id=cart["id"],
        items=cart_items,
        price=total_price
    )
