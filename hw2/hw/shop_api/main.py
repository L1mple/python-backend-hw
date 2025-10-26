from fastapi import FastAPI, Query, Depends
from http import HTTPStatus
from pydantic import BaseModel, Field
from typing import Optional, List
from fastapi.responses import JSONResponse
from fastapi.exceptions import HTTPException
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .database import get_session, ItemModel, CartModel, CartItemModel

app = FastAPI(title="Shop API")

class ItemCreate(BaseModel):
    name: str
    price: float = Field(gt=0)

class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = Field(None, gt=0)

    class Config:
        extra = "forbid"

    @classmethod
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

    def __init__(self, **data):
        if 'deleted' in data:
            raise ValueError("Cannot update 'deleted' field")
        super().__init__(**data)

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
    items: List[CartItem]
    price: float

@app.post("/item", status_code=HTTPStatus.CREATED)
async def create_item(
    item_data: ItemCreate,
    session: AsyncSession = Depends(get_session)
) -> Item:
    new_item = ItemModel(
        name=item_data.name,
        price=item_data.price,
        deleted=False
    )
    session.add(new_item)
    await session.commit()
    await session.refresh(new_item)
    return Item(
        id=new_item.id,
        name=new_item.name,
        price=float(new_item.price),
        deleted=new_item.deleted
    )

@app.get("/item/{item_id}")
async def get_item(
    item_id: int,
    session: AsyncSession = Depends(get_session)
) -> Item:
    result = await session.execute(
        select(ItemModel).where(ItemModel.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return Item(
        id=item.id,
        name=item.name,
        price=float(item.price),
        deleted=item.deleted
    )

@app.get("/item")
async def get_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = False,
    session: AsyncSession = Depends(get_session)
) -> List[Item]:
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

    return [
        Item(id=item.id, name=item.name, price=float(item.price), deleted=item.deleted)
        for item in items
    ]

@app.put("/item/{item_id}")
async def update_item(
    item_id: int,
    item_data: ItemCreate,
    session: AsyncSession = Depends(get_session)
) -> Item:
    result = await session.execute(
        select(ItemModel).where(ItemModel.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    item.name = item_data.name
    item.price = item_data.price
    await session.commit()
    await session.refresh(item)
    return Item(
        id=item.id,
        name=item.name,
        price=float(item.price),
        deleted=item.deleted
    )

@app.patch("/item/{item_id}")
async def patch_item(
    item_id: int,
    item_data: ItemUpdate,
    session: AsyncSession = Depends(get_session)
) -> Item:
    result = await session.execute(
        select(ItemModel).where(ItemModel.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    if item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_MODIFIED)

    if item_data.name is not None:
        item.name = item_data.name
    if item_data.price is not None:
        item.price = item_data.price

    await session.commit()
    await session.refresh(item)
    return Item(
        id=item.id,
        name=item.name,
        price=float(item.price),
        deleted=item.deleted
    )

@app.delete("/item/{item_id}")
async def delete_item(
    item_id: int,
    session: AsyncSession = Depends(get_session)
) -> Item:
    result = await session.execute(
        select(ItemModel).where(ItemModel.id == item_id)
    )
    item = result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    item.deleted = True
    await session.commit()
    await session.refresh(item)
    return Item(
        id=item.id,
        name=item.name,
        price=float(item.price),
        deleted=item.deleted
    )

@app.post("/cart", status_code=HTTPStatus.CREATED)
async def create_cart(session: AsyncSession = Depends(get_session)):
    new_cart = CartModel()
    session.add(new_cart)
    await session.commit()
    await session.refresh(new_cart)

    return JSONResponse(
        content={"id": new_cart.id},
        status_code=HTTPStatus.CREATED,
        headers={"location": f"/cart/{new_cart.id}"}
    )

@app.get("/cart/{cart_id}")
async def get_cart(
    cart_id: int,
    session: AsyncSession = Depends(get_session)
) -> Cart:
    result = await session.execute(
        select(CartModel)
        .where(CartModel.id == cart_id)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemModel.item))
    )
    cart = result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    total_price = 0.0
    cart_items = []
    for ci in cart.cart_items:
        cart_items.append(CartItem(
            id=ci.item_id,
            name=ci.item.name,
            quantity=ci.quantity,
            available=not ci.item.deleted
        ))
        if not ci.item.deleted:
            total_price += float(ci.item.price) * ci.quantity

    return Cart(id=cart.id, items=cart_items, price=total_price)

@app.get("/cart")
async def get_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    session: AsyncSession = Depends(get_session)
) -> List[Cart]:
    result = await session.execute(
        select(CartModel).options(
            selectinload(CartModel.cart_items).selectinload(CartItemModel.item)
        )
    )
    carts = result.scalars().all()

    filtered_carts = []
    for cart in carts:
        total_price = 0.0
        total_quantity = 0
        cart_items = []

        for ci in cart.cart_items:
            cart_items.append(CartItem(
                id=ci.item_id,
                name=ci.item.name,
                quantity=ci.quantity,
                available=not ci.item.deleted
            ))
            total_quantity += ci.quantity
            if not ci.item.deleted:
                total_price += float(ci.item.price) * ci.quantity

        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        filtered_carts.append(Cart(id=cart.id, items=cart_items, price=total_price))

    return filtered_carts[offset:offset + limit]

@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(
    cart_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_session)
) -> Cart:
    cart_result = await session.execute(
        select(CartModel)
        .where(CartModel.id == cart_id)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemModel.item))
    )
    cart = cart_result.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    item_result = await session.execute(
        select(ItemModel).where(ItemModel.id == item_id)
    )
    item = item_result.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)

    existing_cart_item = await session.execute(
        select(CartItemModel).where(
            and_(CartItemModel.cart_id == cart_id, CartItemModel.item_id == item_id)
        )
    )
    existing = existing_cart_item.scalar_one_or_none()

    if existing:
        existing.quantity += 1
    else:
        new_cart_item = CartItemModel(
            cart_id=cart_id,
            item_id=item_id,
            quantity=1
        )
        session.add(new_cart_item)

    await session.commit()

    await session.refresh(cart)
    result = await session.execute(
        select(CartModel)
        .where(CartModel.id == cart_id)
        .options(selectinload(CartModel.cart_items).selectinload(CartItemModel.item))
    )
    cart = result.scalar_one()

    total_price = 0.0
    cart_items = []
    for ci in cart.cart_items:
        cart_items.append(CartItem(
            id=ci.item_id,
            name=ci.item.name,
            quantity=ci.quantity,
            available=not ci.item.deleted
        ))
        if not ci.item.deleted:
            total_price += float(ci.item.price) * ci.quantity

    return Cart(id=cart.id, items=cart_items, price=total_price)
