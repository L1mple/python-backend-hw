from fastapi import FastAPI, HTTPException, status, Response, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import models
import database

app = FastAPI(title="Shop API")

# Создание таблиц
models.Base.metadata.create_all(bind=database.engine)

# Модели Pydantic
class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float

# Dependency
def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Вспомогательные функции
def calculate_cart_price(db: Session, cart_id: int):
    cart_items = db.query(models.CartItem).filter(models.CartItem.cart_id == cart_id).all()
    total = 0.0
    for cart_item in cart_items:
        if cart_item.item and not cart_item.item.deleted:
            total += cart_item.item.price * cart_item.quantity
    return total

# API для корзин
@app.post("/cart", status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response, db: Session = Depends(get_db)):
    db_cart = models.Cart()
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    response.headers["Location"] = f"/cart/{db_cart.id}"
    return {"id": db_cart.id}

@app.get("/cart/{cart_id}", response_model=CartResponse)
async def get_cart(cart_id: int, db: Session = Depends(get_db)):
    db_cart = db.query(models.Cart).filter(models.Cart.id == cart_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    cart_items = db.query(models.CartItem).filter(models.CartItem.cart_id == cart_id).all()
    response_items = []
    
    for cart_item in cart_items:
        available = cart_item.item is not None and not cart_item.item.deleted
        response_items.append(CartItemResponse(
            id=cart_item.item_id,
            name=cart_item.item.name if cart_item.item else "Unknown",
            quantity=cart_item.quantity,
            available=available
        ))
    
    price = calculate_cart_price(db, cart_id)
    
    return CartResponse(
        id=cart_id,
        items=response_items,
        price=price
    )

@app.get("/cart")
async def get_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if offset < 0:
        raise HTTPException(status_code=422, detail="Offset must be non-negative")
    if limit <= 0:
        raise HTTPException(status_code=422, detail="Limit must be positive")
    
    carts = db.query(models.Cart).offset(offset).limit(limit).all()
    result = []
    
    for cart in carts:
        cart_items = db.query(models.CartItem).filter(models.CartItem.cart_id == cart.id).all()
        response_items = []
        
        for cart_item in cart_items:
            available = cart_item.item is not None and not cart_item.item.deleted
            response_items.append({
                "id": cart_item.item_id,
                "name": cart_item.item.name if cart_item.item else "Unknown",
                "quantity": cart_item.quantity,
                "available": available
            })
        
        price = calculate_cart_price(db, cart.id)
        total_quantity = sum(item["quantity"] for item in response_items)
        
        # Фильтрация
        if min_price is not None and price < min_price:
            continue
        if max_price is not None and price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        
        result.append({
            "id": cart.id,
            "items": response_items,
            "price": price
        })
    
    return result

@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    db_cart = db.query(models.Cart).filter(models.Cart.id == cart_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item or db_item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Проверяем, есть ли товар уже в корзине
    existing_cart_item = db.query(models.CartItem).filter(
        models.CartItem.cart_id == cart_id,
        models.CartItem.item_id == item_id
    ).first()
    
    if existing_cart_item:
        existing_cart_item.quantity += 1
    else:
        new_cart_item = models.CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(new_cart_item)
    
    db.commit()
    return {"message": "Item added to cart"}

# API для товаров
@app.post("/item", status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    db_item = models.Item(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.get("/item/{item_id}")
async def get_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item or db_item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return db_item

@app.get("/item")
async def get_items(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db)
):
    if offset < 0:
        raise HTTPException(status_code=422, detail="Offset must be non-negative")
    if limit <= 0:
        raise HTTPException(status_code=422, detail="Limit must be positive")
    
    query = db.query(models.Item)
    if not show_deleted:
        query = query.filter(models.Item.deleted == False)
    if min_price is not None:
        query = query.filter(models.Item.price >= min_price)
    if max_price is not None:
        query = query.filter(models.Item.price <= max_price)
    
    items = query.offset(offset).limit(limit).all()
    return items

@app.put("/item/{item_id}")
async def update_item(item_id: int, item: ItemCreate, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item or db_item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db_item.name = item.name
    db_item.price = item.price
    db.commit()
    db.refresh(db_item)
    return db_item

@app.patch("/item/{item_id}")
async def partial_update_item(item_id: int, item_update: Dict[str, Any], db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item or db_item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if "deleted" in item_update:
        raise HTTPException(status_code=422, detail="Cannot modify deleted field")
    
    allowed_fields = {"name", "price"}
    for field, value in item_update.items():
        if field in allowed_fields:
            setattr(db_item, field, value)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/item/{item_id}")
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    db_item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db_item.deleted = True
    db.commit()
    return {"message": "Item deleted"}