from fastapi import FastAPI, Depends, HTTPException, status, Query
from fastapi.responses import JSONResponse
from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey
from sqlalchemy.orm import relationship, sessionmaker, declarative_base
from sqlalchemy import create_engine
from typing import List, Optional
from prometheus_client import Counter, Histogram, generate_latest, REGISTRY
from starlette.responses import Response
import time
import os

# Database setup
# SQLALCHEMY_DATABASE_URL = "sqlite:///./shop.db"
SQLALCHEMY_DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "mysql+pymysql://user:password@mysql:3306/shop_db"
)
engine = create_engine(SQLALCHEMY_DATABASE_URL)  #, connect_args={"check_same_thread": False}
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP Requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Models
class Item(Base):
    __tablename__ = "items"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    deleted = Column(Boolean, default=False)

class CartItem(Base):
    __tablename__ = "cart_items"
    
    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id"))
    item_id = Column(Integer, ForeignKey("items.id"))
    quantity = Column(Integer, default=1)
    
    item = relationship("Item")

class Cart(Base):
    __tablename__ = "carts"
    
    id = Column(Integer, primary_key=True, index=True)
    items = relationship("CartItem", cascade="all, delete-orphan")

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shop API")

# Pydantic schemas
from pydantic import BaseModel, ValidationError

class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float

class CartCreateResponse(BaseModel):
    id: int

class ItemBase(BaseModel):
    name: str
    price: float

class ItemCreate(ItemBase):
    pass

class ItemUpdate(ItemBase):
    pass

class ItemResponse(ItemBase):
    id: int
    deleted: bool

    class Config:
        from_attributes = True

class ItemPatch(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    class Config:
        extra = "forbid"

# Middleware для сбора метрик
@app.middleware("http")
async def monitor_requests(request, call_next):
    start_time = time.time()
    response = await call_next(request)
    
    # Получаем путь endpoint'а
    endpoint = request.url.path
    method = request.method
    
    # Игнорируем метрики для самого endpoint'а /metrics
    if endpoint != "/metrics":
        REQUEST_COUNT.labels(method=method, endpoint=endpoint, status=response.status_code).inc()
        REQUEST_LATENCY.labels(method=method, endpoint=endpoint).observe(time.time() - start_time)
    
    return response

# Endpoint для Prometheus метрик
@app.get("/metrics")
async def metrics():
    return Response(generate_latest(REGISTRY), media_type="text/plain")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

# Cart endpoints
@app.post("/cart", status_code=status.HTTP_201_CREATED)
def create_cart(db: SessionLocal = Depends(get_db)):
    db_cart = Cart()
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={"id": db_cart.id},
        headers={"Location": f"/cart/{db_cart.id}"}
    )

@app.get("/cart/{cart_id}", response_model=CartResponse)
def get_cart(cart_id: int, db: SessionLocal = Depends(get_db)):
    db_cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not db_cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    total_price = 0.0
    cart_items = []
    
    for cart_item in db_cart.items:
        item = cart_item.item
        available = not item.deleted
        total_price += item.price * cart_item.quantity
        
        cart_items.append({
            "id": item.id,
            "name": item.name,
            "quantity": cart_item.quantity,
            "available": available
        })
    
    return {
        "id": db_cart.id,
        "items": cart_items,
        "price": total_price
    }

@app.get("/cart")
def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: SessionLocal = Depends(get_db)
):
    carts = db.query(Cart).all()  # Получаем все корзины
    
    result = []
    for db_cart in carts:
        total_price = 0.0
        total_quantity = 0  # Добавляем подсчет общего количества товаров
        cart_items = []
        
        for cart_item in db_cart.items:
            item = cart_item.item
            available = not item.deleted
            total_price += item.price * cart_item.quantity
            total_quantity += cart_item.quantity  # Суммируем количество
            
            cart_items.append({
                "id": item.id,
                "name": item.name,
                "quantity": cart_item.quantity,
                "available": available
            })
        
        cart_data = {
            "id": db_cart.id,
            "items": cart_items,
            "price": total_price
        }
        
        # Применяем фильтры
        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
            
        result.append(cart_data)
    
    # Применяем пагинацию после фильтрации
    return result[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db: SessionLocal = Depends(get_db)):
    cart = db.query(Cart).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    item = db.query(Item).filter(Item.id == item_id, Item.deleted == False).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Check if item already in cart
    cart_item = db.query(CartItem).filter(
        CartItem.cart_id == cart_id, 
        CartItem.item_id == item_id
    ).first()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(cart_item)
    
    db.commit()
    return {"message": "Item added to cart"}

# Item endpoints
@app.post("/item", response_model=ItemResponse, status_code=status.HTTP_201_CREATED)
def create_item(item: ItemCreate, db: SessionLocal = Depends(get_db)):
    db_item = Item(name=item.name, price=item.price)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": db_item.price,
        "deleted": db_item.deleted
    }

@app.get("/item/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: SessionLocal = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item or db_item.deleted:  # Добавляем проверку на deleted
        raise HTTPException(status_code=404, detail="Item not found")
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": db_item.price,
        "deleted": db_item.deleted
    }

@app.get("/item", response_model=List[ItemResponse])
def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, ge=1),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
    db: SessionLocal = Depends(get_db)
):
    query = db.query(Item)
    
    if not show_deleted:
        query = query.filter(Item.deleted == False)
    
    if min_price is not None:
        query = query.filter(Item.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Item.price <= max_price)
    
    items = query.offset(offset).limit(limit).all()
    
    return [
        {
            "id": item.id,
            "name": item.name,
            "price": item.price,
            "deleted": item.deleted
        }
        for item in items
    ]

@app.put("/item/{item_id}", response_model=ItemResponse)
def update_item(item_id: int, item: ItemUpdate, db: SessionLocal = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item or db_item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db_item.name = item.name
    db_item.price = item.price
    db.commit()
    db.refresh(db_item)
    
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": db_item.price,
        "deleted": db_item.deleted
    }

@app.patch("/item/{item_id}", response_model=ItemResponse)
def patch_item(item_id: int, item_update: dict, db: SessionLocal = Depends(get_db)):
    # Проверяем, что нет поля deleted в обновлении
    if "deleted" in item_update:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Cannot update deleted field via PATCH"
        )
    
    # Валидируем поля с помощью Pydantic
    try:
        validated_data = ItemPatch(**item_update).dict(exclude_unset=True)
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid fields in update data: {e}"
        )
    
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item or db_item.deleted:
        raise HTTPException(
            status_code=status.HTTP_304_NOT_MODIFIED,
            detail="Item not found or deleted"
        )
    
    # Обновляем только валидированные поля
    for field, value in validated_data.items():
        if hasattr(db_item, field):
            setattr(db_item, field, value)
    
    db.commit()
    db.refresh(db_item)
    
    return {
        "id": db_item.id,
        "name": db_item.name,
        "price": db_item.price,
        "deleted": db_item.deleted
    }

@app.delete("/item/{item_id}")
def delete_item(item_id: int, db: SessionLocal = Depends(get_db)):
    db_item = db.query(Item).filter(Item.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db_item.deleted = True
    db.commit()
    return {"message": "Item deleted"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

@app.on_event("startup")
def startup_event():
    # Создаем таблицы при запуске приложения
    Base.metadata.create_all(bind=engine)
