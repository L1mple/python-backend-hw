from fastapi import FastAPI, HTTPException, Response, Query, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from http import HTTPStatus
import random 
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemUpdate(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)

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
    items: list[CartItem]
    price: float

class CartIdResponse(BaseModel):
    id: int

items_db: dict[int, Item] = {}
carts_db: dict[int, dict[int, int]] = {} 
item_counter = 0
cart_counter = 0

chat_rooms: dict[str, list[tuple[WebSocket, str]]] = {}

def generate_username():
    adjectives = ["Happy", "Clever", "Brave", "Swift", "Strong", "Wise", "Cool", "Epic"]
    nouns = ["Panda", "Tiger", "Eagle", "Dragon", "Phoenix", "Wolf", "Bear", "Fox"]
    number = random.randint(100, 999)
    return f"{random.choice(adjectives)}{random.choice(nouns)}{number}"

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/item", status_code=HTTPStatus.CREATED, response_model=Item)
def create_item(item: ItemCreate):
    global item_counter
    item_counter += 1
    
    new_item = Item(
        id=item_counter,
        name=item.name,
        price=item.price,
        deleted=False
    )
    items_db[item_counter] = new_item
    return new_item


@app.get("/item/{item_id}", response_model=Item)
def get_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    item = items_db[item_id]
    if item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    return item


@app.get("/item", response_model=list[Item])
def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False
):
    filtered_items = []
    
    for item in items_db.values():
        if not show_deleted and item.deleted:
            continue
        
        if min_price is not None and item.price < min_price:
            continue
        if max_price is not None and item.price > max_price:
            continue
        
        filtered_items.append(item)
    
    return filtered_items[offset:offset + limit]


@app.put("/item/{item_id}", response_model=Item)
def update_item(item_id: int, item: ItemUpdate):
    if item_id not in items_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    existing_item = items_db[item_id]
    existing_item.name = item.name
    existing_item.price = item.price
    
    return existing_item


@app.patch("/item/{item_id}", response_model=Item)
def patch_item(item_id: int, item: ItemPatch):
    if item_id not in items_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    existing_item = items_db[item_id]
    
    if existing_item.deleted:
        return Response(status_code=HTTPStatus.NOT_MODIFIED)
    
    if item.name is not None:
        existing_item.name = item.name
    if item.price is not None:
        existing_item.price = item.price
    
    return existing_item


@app.delete("/item/{item_id}")
def delete_item(item_id: int):
    if item_id not in items_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    items_db[item_id].deleted = True
    return Response(status_code=HTTPStatus.OK)


@app.post("/cart", status_code=HTTPStatus.CREATED, response_model=CartIdResponse)
def create_cart(response: Response):
    global cart_counter
    cart_counter += 1
    
    carts_db[cart_counter] = {}
    response.headers["location"] = f"/cart/{cart_counter}"
    
    return CartIdResponse(id=cart_counter)


@app.get("/cart/{cart_id}", response_model=Cart)
def get_cart(cart_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    
    cart_items_data = carts_db[cart_id]
    cart_items = []
    total_price = 0.0
    
    for item_id, quantity in cart_items_data.items():
        if item_id in items_db:
            item = items_db[item_id]
            cart_items.append(CartItem(
                id=item.id,
                name=item.name,
                quantity=quantity,
                available=not item.deleted
            ))
            if not item.deleted:
                total_price += item.price * quantity
    
    return Cart(
        id=cart_id,
        items=cart_items,
        price=total_price
    )


@app.get("/cart", response_model=list[Cart])
def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
):
    filtered_carts = []
    
    for cart_id in carts_db.keys():
        cart = get_cart(cart_id)
        

        total_quantity = sum(item.quantity for item in cart.items)
        
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
        
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        
        filtered_carts.append(cart)
    
    return filtered_carts[offset:offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    if cart_id not in carts_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    
    if item_id not in items_db:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    if item_id in carts_db[cart_id]:
        carts_db[cart_id][item_id] += 1
    else:
        carts_db[cart_id][item_id] = 1
    
    return Response(status_code=HTTPStatus.OK)

@app.websocket("/chat/{chat_name}")
async def chat_endpoint(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    
   
    username = generate_username()
    
    
    if chat_name not in chat_rooms:
        chat_rooms[chat_name] = []
    
    
    chat_rooms[chat_name].append((websocket, username))
    
    try:
        while True:
            message = await websocket.receive_text()
            
            formatted_message = f"{username} :: {message}"
            
            for ws, user in chat_rooms[chat_name]:
                try:
                    await ws.send_text(formatted_message)
                except:
                    pass
    
    except WebSocketDisconnect:
        chat_rooms[chat_name] = [
            (ws, user) for ws, user in chat_rooms[chat_name] 
            if ws != websocket
        ]
        
        if not chat_rooms[chat_name]:
            del chat_rooms[chat_name]