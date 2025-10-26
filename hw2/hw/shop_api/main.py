from fastapi import FastAPI, HTTPException, Query, status, Response, WebSocket, WebSocketDisconnect, Depends
from pydantic import BaseModel, Field, ConfigDict, computed_field
from typing import List, Optional, Dict
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

import uuid
from collections import defaultdict
from contextlib import asynccontextmanager

from prometheus_fastapi_instrumentator import Instrumentator

from .database import get_session, init_db
from .models import ItemModel, CartModel, CartItemModel


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="Shop API", lifespan=lifespan)

Instrumentator().instrument(app).expose(app)


class Item(BaseModel):
    id: int
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)
    deleted: bool = False

class ItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    price: float = Field(..., gt=0)

class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[float] = Field(None, gt=0)

class CartItem(BaseModel):
    id: int
    name: str
    quantity: int = Field(..., ge=0)
    available: bool = True

class Cart(BaseModel):
    id: int
    items: List[CartItem] = []
    price: float = 0.0


@app.post("/item", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate, session: AsyncSession = Depends(get_session)):
    new_item = ItemModel(name=item.name, price=item.price, deleted=False)
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    return Item(id=new_item.id, name=new_item.name, price=new_item.price, deleted=new_item.deleted)

@app.get("/item/{item_id}", response_model=Item)
async def get_item(item_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(ItemModel).where(and_(ItemModel.id == item_id, ItemModel.deleted == False))
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

@app.get("/item", response_model=List[Item])
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
    session: AsyncSession = Depends(get_session)
):
    query = select(ItemModel)
    
    if not show_deleted:
        query = query.where(ItemModel.deleted == False)
    
    if min_price is not None:
        query = query.where(ItemModel.price >= min_price)
    
    if max_price is not None:
        query = query.where(ItemModel.price <= max_price)
    
    query = query.offset(offset).limit(limit)
    
    result = await session.execute(query)
    items = result.scalars().all()
    
    return [Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted) for item in items]

@app.put("/item/{item_id}", response_model=Item)
async def replace_item(item_id: int, new_item: ItemCreate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemModel).where(ItemModel.id == item_id))
    item = result.scalar_one_or_none()
    
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.name = new_item.name
    item.price = new_item.price
    await session.commit()
    await session.refresh(item)
    
    return Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

@app.patch("/item/{item_id}", response_model=Item)
async def patch_item(item_id: int, upd: ItemUpdate, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemModel).where(ItemModel.id == item_id))
    item = result.scalar_one_or_none()
    
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if item.deleted:
        raise HTTPException(status_code=304, detail="Item not modified")
    
    update_data = upd.model_dump(exclude_unset=True)
    
    for key, value in update_data.items():
        setattr(item, key, value)
    
    await session.commit()
    await session.refresh(item)
    
    return Item(id=item.id, name=item.name, price=item.price, deleted=item.deleted)

@app.delete("/item/{item_id}", status_code=status.HTTP_200_OK)
async def delete_item(item_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(ItemModel).where(ItemModel.id == item_id))
    item = result.scalar_one_or_none()
    
    if item is not None:
        item.deleted = True
        await session.commit()
    
    return Response(status_code=status.HTTP_200_OK)


@app.post("/cart", response_model=Cart, status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response, session: AsyncSession = Depends(get_session)):
    new_cart = CartModel()
    session.add(new_cart)
    await session.commit()
    await session.refresh(new_cart)
    
    response.headers["Location"] = f"/cart/{new_cart.id}"
    return Cart(id=new_cart.id, items=[], price=0.0)

@app.get("/cart/{cart_id}", response_model=Cart)
async def get_cart(cart_id: int, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(CartModel).where(CartModel.id == cart_id)
    )
    cart = result.scalar_one_or_none()
    
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Загружаем cart_items
    cart_items_result = await session.execute(
        select(CartItemModel).where(CartItemModel.cart_id == cart_id)
    )
    cart_items = cart_items_result.scalars().all()
    
    items = []
    total_price = 0.0
    
    for cart_item in cart_items:
        # Загружаем информацию о товаре
        item_result = await session.execute(
            select(ItemModel).where(ItemModel.id == cart_item.item_id)
        )
        item = item_result.scalar_one_or_none()
        
        if item:
            items.append(CartItem(
                id=item.id,
                name=item.name,
                quantity=cart_item.quantity,
                available=not item.deleted
            ))
            total_price += item.price * cart_item.quantity
    
    return Cart(id=cart.id, items=items, price=total_price)

@app.get("/cart", response_model=List[Cart])
async def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    session: AsyncSession = Depends(get_session)
):
    # Получаем все корзины
    result = await session.execute(select(CartModel))
    all_carts = result.scalars().all()
    
    carts = []
    
    for cart in all_carts:
        # Загружаем cart_items для каждой корзины
        cart_items_result = await session.execute(
            select(CartItemModel).where(CartItemModel.cart_id == cart.id)
        )
        cart_items = cart_items_result.scalars().all()
        
        items = []
        total_price = 0.0
        total_quantity = 0
        
        for cart_item in cart_items:
            # Загружаем информацию о товаре
            item_result = await session.execute(
                select(ItemModel).where(ItemModel.id == cart_item.item_id)
            )
            item = item_result.scalar_one_or_none()
            
            if item:
                items.append(CartItem(
                    id=item.id,
                    name=item.name,
                    quantity=cart_item.quantity,
                    available=not item.deleted
                ))
                total_price += item.price * cart_item.quantity
                total_quantity += cart_item.quantity
        
        # Фильтрация
        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        
        carts.append(Cart(id=cart.id, items=items, price=total_price))
    
    # Применяем offset и limit
    return carts[offset : offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart, status_code=status.HTTP_200_OK)
async def add_to_cart(cart_id: int, item_id: int, session: AsyncSession = Depends(get_session)):
    # Проверяем существование корзины
    cart_result = await session.execute(select(CartModel).where(CartModel.id == cart_id))
    cart = cart_result.scalar_one_or_none()
    
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    # Проверяем существование товара
    item_result = await session.execute(select(ItemModel).where(ItemModel.id == item_id))
    item = item_result.scalar_one_or_none()
    
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    # Проверяем, есть ли уже такой товар в корзине
    cart_item_result = await session.execute(
        select(CartItemModel).where(
            and_(CartItemModel.cart_id == cart_id, CartItemModel.item_id == item_id)
        )
    )
    cart_item = cart_item_result.scalar_one_or_none()
    
    if cart_item:
        cart_item.quantity += 1
    else:
        new_cart_item = CartItemModel(cart_id=cart_id, item_id=item_id, quantity=1)
        session.add(new_cart_item)
    
    await session.commit()
    return await get_cart(cart_id, session)


rooms: Dict[str, Dict[WebSocket, str]] = defaultdict(dict)

@app.websocket("/chat/{chat_name}")
async def chat_ws(websocket: WebSocket, chat_name: str):
    await websocket.accept()
    username = f"user-{uuid.uuid4().hex[:8]}"
    rooms[chat_name][websocket] = username

    try:
        while True:
            message = await websocket.receive_text()
            formatted = f"{username} :: {message}"

            for ws, _uname in list(rooms[chat_name].items()):
                if ws is websocket:
                    continue
                try:
                    await ws.send_text(formatted)
                except Exception:
                    rooms[chat_name].pop(ws, None)

    except WebSocketDisconnect:
        pass
    finally:
        rooms[chat_name].pop(websocket, None)
        if not rooms[chat_name]:
            rooms.pop(chat_name, None)
