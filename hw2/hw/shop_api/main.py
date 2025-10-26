import os
import random
from typing import Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Response, Query, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field, ConfigDict
from http import HTTPStatus

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Float, Boolean, Integer, ForeignKey, select, delete, update
from prometheus_fastapi_instrumentator import Instrumentator


DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://shop_user:shop_password@localhost:5432/shop_db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

class ItemDB(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    price: Mapped[float] = mapped_column(Float)
    deleted: Mapped[bool] = mapped_column(Boolean, default=False)

class CartDB(Base):
     __tablename__ = "carts"

     id: Mapped[int] = mapped_column(primary_key=True)

class CartItemDB(Base):
    __tablename__ = "cart_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    cart_id: Mapped[int] = mapped_column(ForeignKey("carts.id", ondelete="CASCADE"))
    item_id: Mapped[int] = mapped_column(ForeignKey("items.id", ondelete="CASCADE"))
    quantity: Mapped[int] = mapped_column(Integer, default=1)

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

@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(title="Shop API", lifespan=lifespan)

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)

chat_rooms: dict[str, list[tuple[WebSocket, str]]] = {}

def generate_username():  # pragma: no cover
    adjectives = ["Happy", "Clever", "Brave", "Swift", "Strong", "Wise", "Cool", "Epic"]
    nouns = ["Panda", "Tiger", "Eagle", "Dragon", "Phoenix", "Wolf", "Bear", "Fox"]
    number = random.randint(100, 999)
    return f"{random.choice(adjectives)}{random.choice(nouns)}{number}"

async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        yield session

@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.post("/item", status_code=HTTPStatus.CREATED, response_model=Item)
async def create_item(item: ItemCreate, session: AsyncSession = Depends(get_session)):
    new_item = ItemDB(name=item.name, price=item.price, deleted=False)
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    return Item(id=new_item.id, name=new_item.name, price=new_item.price, deleted=new_item.deleted)


@app.get("/item/{item_id}", response_model=Item)
async def get_item(item_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    return Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

@app.get("/item", response_model=List[Item])
async def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
    session: AsyncSession = Depends(get_session)
):
    query = select(ItemDB)
    
    if not show_deleted:
        query = query.where(ItemDB.deleted == False)
    
    if min_price is not None:
        query = query.where(ItemDB.price >= min_price)
    
    if max_price is not None:
        query = query.where(ItemDB.price <= max_price)
    
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    return [Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted) for item in items]

@app.put("/item/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    existing_item = result.scalar_one_or_none()
    
    if not existing_item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    existing_item.name = item.name
    existing_item.price = item.price
    
    await session.commit()
    await session.refresh(existing_item)
    
    return Item(id=existing_item.id, name=existing_item.name, price=existing_item.price, deleted=existing_item.deleted)



@app.patch("/item/{item_id}", response_model=Item)
async def patch_item(item_id: int, item: ItemPatch, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    existing_item = result.scalar_one_or_none()
    
    if not existing_item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    if existing_item.deleted:
        return Response(status_code=HTTPStatus.NOT_MODIFIED)
    
    if item.name is not None:
        existing_item.name = item.name
    if item.price is not None:
        existing_item.price = item.price
    
    await session.commit()
    await session.refresh(existing_item)
    
    return Item(id=existing_item.id, name=existing_item.name, price=existing_item.price, deleted=existing_item.deleted)


@app.delete("/item/{item_id}")
async def delete_item(item_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    item = result.scalar_one_or_none()
    
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    item.deleted = True
    await session.commit()
    
    return Response(status_code=HTTPStatus.OK)



@app.post("/cart", status_code=HTTPStatus.CREATED, response_model=CartIdResponse)
async def create_cart(response: Response, session: AsyncSession = Depends(get_session)):
    new_cart = CartDB()
    session.add(new_cart)
    await session.commit()
    await session.refresh(new_cart)
    
    response.headers["location"] = f"/cart/{new_cart.id}"
    return CartIdResponse(id=new_cart.id)


@app.get("/cart/{cart_id}", response_model=Cart)
async def get_cart(cart_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(CartDB).where(CartDB.id == cart_id))
    cart = result.scalar_one_or_none()
    
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    
    query = select(CartItemDB, ItemDB).join(ItemDB, CartItemDB.item_id == ItemDB.id).where(CartItemDB.cart_id == cart_id)
    result = await session.execute(query)
    cart_items_data = result.all()
    
    cart_items = []
    total_price = 0.0
    
    for cart_item, item in cart_items_data:
        cart_items.append(CartItem(
            id=item.id,
            name=item.name,
            quantity=cart_item.quantity,
            available=not item.deleted
        ))
        if not item.deleted:
            total_price += item.price * cart_item.quantity
    
    return Cart(id=cart_id, items=cart_items, price=total_price)


@app.get("/cart", response_model=List[Cart])
async def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(CartDB.id).offset(offset).limit(limit))
    cart_ids = result.scalars().all()
    
    carts = []
    for cart_id in cart_ids:
        cart = await get_cart(cart_id, session)
        
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
        
        total_quantity = sum(item.quantity for item in cart.items)
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        
        carts.append(cart)
    
    return carts


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(CartDB).where(CartDB.id == cart_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    
    result = await session.execute(select(ItemDB).where(ItemDB.id == item_id))
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    
    result = await session.execute(
        select(CartItemDB).where(CartItemDB.cart_id == cart_id, CartItemDB.item_id == item_id)
    )
    cart_item = result.scalar_one_or_none()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItemDB(cart_id=cart_id, item_id=item_id, quantity=1)
        session.add(cart_item)
    
    await session.commit()
    return Response(status_code=HTTPStatus.OK)

@app.websocket("/chat/{chat_name}")
async def chat_endpoint(websocket: WebSocket, chat_name: str):  # pragma: no cover
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