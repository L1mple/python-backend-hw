from fastapi import FastAPI, HTTPException, Response, status
from typing import List, Optional
from pydantic import BaseModel, ConfigDict
from prometheus_fastapi_instrumentator import Instrumentator
# Наша pydantic модель для Item
class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

# Наша pydantic модель для CartItem
class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

# Наша pydantic модель для Cart
class Cart(BaseModel):
    id: int
    items: List[CartItem] = []
    price: float = 0.0

# Условные базы данных
carts_db = {}
items_db = {}

# Инициализация FastAPI приложения
app = FastAPI(title="Cart API", version="1.0.0")
Instrumentator().instrument(app).expose(app)

class ItemCreateUpdate(BaseModel):
    name: str
    price: float

class CartCreateResponse(BaseModel):
    id: int

class ItemPatchUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: Optional[str] = None
    price: Optional[float] = None

class ItemCreateUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: str
    price: float



@app.post("/cart", response_model=CartCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response):
    new_id = max(carts_db.keys(), default=0) + 1
    
    new_cart = Cart(
        id=new_id,
        items=[],
        price=0.0
    )
    
    carts_db[new_id] = new_cart
    response.headers["Location"] = f"/cart/{new_id}"

    return CartCreateResponse(id=new_id)

@app.get("/cart/{cart_id}", response_model=Cart)
async def get_cart(cart_id: int):
    if cart_id not in carts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    return carts_db[cart_id]

@app.get("/cart", response_model=List[Cart])
async def list_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None
):
    if offset < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Offset must be >= 0"
        )
    
    if limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Limit must be > 0"
        )
    
    if min_quantity is not None and min_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_quantity must be >= 0"
        )
    
    if max_quantity is not None and max_quantity < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="max_quantity must be >= 0"
        )
    
    if min_price is not None and min_price < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_price must be >= 0"
        )
    
    if max_price is not None and max_price < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="max_price must be >= 0"
        )
    
    if min_price is not None and max_price is not None and min_price > max_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_price must be <= max_price"
        )
    
    if min_quantity is not None and max_quantity is not None and min_quantity > max_quantity:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_quantity must be <= max_quantity"
        )
    
    filtered_carts = []
    
    for cart in carts_db.values():
        total_quantity = sum(item.quantity for item in cart.items)
        
        price_ok = (min_price is None or cart.price >= min_price) and \
                   (max_price is None or cart.price <= max_price)
        
        quantity_ok = (min_quantity is None or total_quantity >= min_quantity) and \
                      (max_quantity is None or total_quantity <= max_quantity)
        
        if price_ok and quantity_ok:
            filtered_carts.append(cart)
    
    return filtered_carts[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
async def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found"
        )
    
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    item = items_db[item_id]
    
    if item.deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    cart = carts_db[cart_id]
    
    existing_cart_item = None
    for cart_item in cart.items:
        if cart_item.id == item_id:
            existing_cart_item = cart_item
            break
    
    if existing_cart_item:
        existing_cart_item.quantity += 1
    else:
        new_cart_item = CartItem(
            id=item.id,
            name=item.name,
            quantity=1,
            available=not item.deleted
        )
        cart.items.append(new_cart_item)
    
    cart.price = sum(item.price * cart_item.quantity 
                    for cart_item in cart.items 
                    for item in [items_db[cart_item.id]])
    
    return cart


@app.post("/item", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreateUpdate):
    new_id = max(items_db.keys(), default=0) + 1
    
    new_item = Item(
        id=new_id,
        name=item.name,
        price=item.price,
        deleted=False
    )
    
    items_db[new_id] = new_item
    
    return new_item

@app.get("/item/{item_id}", response_model=Item)
async def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    item = items_db[item_id]
    
    if item.deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    return item

@app.get("/item", response_model=List[Item])
async def list_items(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False
):
    if offset < 0 or limit <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Offset must be >= 0 and limit must be > 0"
        )
    if min_price is not None and min_price < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_price must be >= 0"
        )
    
    if max_price is not None and max_price < 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="max_price must be >= 0"
        )
    
    filtered_items = [
        item for item in items_db.values()
        if (show_deleted or not item.deleted) and
           (min_price is None or (item.price is not None and item.price >= min_price)) and
           (max_price is None or (item.price is not None and item.price <= max_price))
    ]
    
    return filtered_items[offset:offset + limit]

@app.put("/item/{item_id}", response_model=Item)
async def update_item_put(item_id: int, item: ItemCreateUpdate):
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    updated_item = Item(
        id=item_id,
        name=item.name,
        price=item.price,
        deleted=False
    )
    
    items_db[item_id] = updated_item
    
    return updated_item

@app.patch("/item/{item_id}", response_model=Item)
async def update_item_patch(item_id: int, item: ItemPatchUpdate):
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    existing_item = items_db[item_id]
    
    if existing_item.deleted:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail="Cannot modify deleted item"
        )
    
    update_data = item.model_dump(exclude_unset=True)
    
    if not update_data:
        return existing_item
    
    updated_item = Item(
        id=item_id,
        name=update_data.get('name', existing_item.name),
        price=update_data.get('price', existing_item.price),
        deleted=existing_item.deleted
    )
    
    items_db[item_id] = updated_item
    return updated_item

@app.delete("/item/{item_id}", response_model=Item)
async def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Item not found"
        )
    
    items_db[item_id].deleted = True
    
    return items_db[item_id]