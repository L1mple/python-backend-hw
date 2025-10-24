from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect, HTTPException, Response, Depends
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy.orm import Session
import random
import string
import uvicorn
from prometheus_fastapi_instrumentator import Instrumentator
from database import get_db, init_db
from models import ItemModel, CartModel, get_cart_items_with_quantity, set_cart_item_quantity

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)
@app.on_event("startup")
def startup():
    init_db()

class ItemBase(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    pass

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)
    model_config = {"extra": "forbid"}

class Item(ItemBase):
    id: int
    deleted: bool = False
    
    class Config:
        from_attributes = True

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    id: int
    items: list[CartItem]
    price: float

# ==================== ЭНДПОИНТЫ ДЛЯ ТОВАРОВ ====================

@app.post("/item", response_model=Item, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    """Создать новый товар"""
    db_item = ItemModel(
        name=item.name,
        price=item.price,
        deleted=False
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@app.patch("/item/{id}", response_model=Item)
def patch_item(id: int, item: ItemPatch, db: Session = Depends(get_db)):
    """Частично обновить товар"""
    db_item = db.query(ItemModel).filter(ItemModel.id == id).first()
    
    if not db_item:
        raise HTTPException(status_code=404)
    
    if db_item.deleted:
        return Response(status_code=304)
    
    if item.name is not None:
        db_item.name = item.name
    if item.price is not None:
        db_item.price = item.price
    
    db.commit()
    db.refresh(db_item)
    return db_item


@app.put("/item/{id}", response_model=Item)
def put_item(id: int, item: ItemUpdate, db: Session = Depends(get_db)):
    """Полностью обновить товар"""
    db_item = db.query(ItemModel).filter(ItemModel.id == id).first()
    
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db_item.name = item.name
    db_item.price = item.price
    
    db.commit()
    db.refresh(db_item)
    return db_item


@app.get("/item", response_model=list[Item])
def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
    db: Session = Depends(get_db)
):
    """Получить список товаров с фильтрацией"""
    query = db.query(ItemModel)
 
    if not show_deleted:
        query = query.filter(ItemModel.deleted == False)

    if min_price is not None:
        query = query.filter(ItemModel.price >= min_price)

    if max_price is not None:
        query = query.filter(ItemModel.price <= max_price)

    items = query.offset(offset).limit(limit).all()
    
    return items


@app.get("/item/{id}", response_model=Item)
def get_item_id(id: int, db: Session = Depends(get_db)):
    """Получить товар по ID"""
    db_item = db.query(ItemModel).filter(
        ItemModel.id == id,
        ItemModel.deleted == False
    ).first()
    
    if not db_item:
        raise HTTPException(status_code=404)
    
    return db_item


@app.delete("/item/{id}", response_model=Item)
def delete_item(id: int, db: Session = Depends(get_db)):
    """Мягкое удаление товара"""
    db_item = db.query(ItemModel).filter(ItemModel.id == id).first()
    
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db_item.deleted = True
    db.commit()
    db.refresh(db_item)
    return db_item


# ==================== ЭНДПОИНТЫ ДЛЯ КОРЗИН ====================

@app.post("/cart", status_code=201)
def post_cart(response: Response, db: Session = Depends(get_db)):
    """Создать новую корзину"""
    new_cart = CartModel()
    db.add(new_cart)
    db.commit()
    db.refresh(new_cart)
    
    response.headers["location"] = f"/cart/{new_cart.id}"
    return {"id": new_cart.id}


@app.get("/cart", response_model=list[Cart])
def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db)
):
    """Получить список корзин с фильтрацией"""
    all_carts = db.query(CartModel).all()
    
    filtered_carts = []
    
    for cart in all_carts:
        items_with_qty = get_cart_items_with_quantity(db, cart.id)
        
        cart_items = []
        total_price = 0.0
        total_quantity = 0
        
        for item, quantity in items_with_qty:
            available = not item.deleted
            cart_items.append({
                "id": item.id,
                "name": item.name,
                "quantity": quantity,
                "available": available
            })
            if available:
                total_price += item.price * quantity
            total_quantity += quantity

        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        
        filtered_carts.append({
            "id": cart.id,
            "items": cart_items,
            "price": total_price
        })
    
    return filtered_carts[offset : offset + limit]


@app.get("/cart/{id}", response_model=Cart)
def get_cart_id(id: int, db: Session = Depends(get_db)):
    """Получить корзину по ID"""
    cart = db.query(CartModel).filter(CartModel.id == id).first()
    
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    items_with_qty = get_cart_items_with_quantity(db, cart.id)
    
    cart_items = []
    total_price = 0.0
    
    for item, quantity in items_with_qty:
        available = not item.deleted
        cart_items.append(CartItem(
            id=item.id,
            name=item.name,
            quantity=quantity,
            available=available
        ))
        if available:
            total_price += item.price * quantity
    
    return Cart(
        id=cart.id,
        items=cart_items,
        price=total_price
    )


@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = db.query(CartModel).filter(CartModel.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    items_with_qty = get_cart_items_with_quantity(db, cart_id)
    current_quantity = 0
    
    for cart_item, quantity in items_with_qty:
        if cart_item.id == item_id:
            current_quantity = quantity
            break
    set_cart_item_quantity(db, cart_id, item_id, current_quantity + 1)
    return get_cart_id(cart_id, db)


# ==================== WEBSOCKET ЧАТ ====================
chat_rooms: dict[str, list[tuple[WebSocket, str]]] = {}

def generate_username() -> str:
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))


@app.websocket("/chat/{chat_name}")
async def websocket_chat(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = generate_username()
    
    if chat_name not in chat_rooms:
        chat_rooms[chat_name] = []
    chat_rooms[chat_name].append((websocket, username))
    
    try:
        while True:
            message = await websocket.receive_text()
            formatted_message = f"{username} :: {message}"
            for client_ws, client_username in chat_rooms[chat_name]:
                await client_ws.send_text(formatted_message)
                
    except WebSocketDisconnect:
        chat_rooms[chat_name] = [
            (ws, user) for ws, user in chat_rooms[chat_name] 
            if ws != websocket
        ]
        if not chat_rooms[chat_name]:
            del chat_rooms[chat_name]


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)