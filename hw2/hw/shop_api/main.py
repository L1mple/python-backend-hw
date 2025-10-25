from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from dao import get_db
from models import Item, Cart, CartItem

app = FastAPI(title="Shop API")

Instrumentator().instrument(app).expose(app)

class ItemDTO(BaseModel):
    name: str
    price: float

class PatchItemDTO(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None

    model_config = ConfigDict(extra="forbid")

class PutItemDTO(BaseModel):
    name: str
    price: float
    deleted: Optional[bool] = False



@app.post("/cart", status_code=201)
async def create_cart(db: AsyncSession = Depends(get_db)):
    cart = Cart()
    db.add(cart)
    await db.commit()
    await db.refresh(cart)
    return JSONResponse(
        status_code=201,
        content={"id": cart.id},
        headers={"Location": f"/cart/{cart.id}"}
    )


@app.get("/cart/{id}")
async def get_cart(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Cart).options(
            selectinload(Cart.cart_items).selectinload(CartItem.item)
        ).where(Cart.id == id)
    )
    cart = result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    return JSONResponse(
        status_code=200,
        content=cart.to_json(),
        headers={"Location": f"/cart/{cart.id}"}
    )

@app.get("/cart")
async def list_carts(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Cart).options(selectinload(Cart.cart_items).selectinload(CartItem.item))
    )
    carts_all = result.scalars().all()

    def valid_cart(cart: Cart) -> bool:
        price = sum(ci.get_total_price() for ci in getattr(cart, "cart_items", []))
        qty = sum((ci.quantity or 0) for ci in getattr(cart, "cart_items", []))
        return (
            (min_price is None or price >= min_price) and
            (max_price is None or price <= max_price) and
            (min_quantity is None or qty >= min_quantity) and
            (max_quantity is None or qty <= max_quantity)
        )

    filtered = [c for c in carts_all if valid_cart(c)]
    sliced = filtered[offset: offset + limit]
    return [c.to_json() for c in sliced]


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Cart).where(Cart.id == cart_id))
    cart = result.scalar_one_or_none()
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")

    result = await db.execute(select(Item).where(Item.id == item_id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    result = await db.execute(
        select(CartItem).where(CartItem.cart_id == cart.id, CartItem.item_id == item.id)
    )
    cart_item = result.scalar_one_or_none()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.id, item_id=item.id, quantity=1)
        db.add(cart_item)

    await db.commit()
    return {"message": "Item added to cart"}


@app.post("/item", status_code=201)
async def create_item(item_dto: ItemDTO, db: AsyncSession = Depends(get_db)):
    item = Item(name=item_dto.name, price=item_dto.price)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return JSONResponse(
        status_code=201,
        content=item.to_json(),
        headers={"Location": f"/item/{item.id}"}
    )



@app.get("/item/{id}")
async def get_item(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.id == id))
    item = result.scalar_one_or_none()
    if not item or item.deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return JSONResponse(
        status_code=200,
        content=item.to_json(),
        headers={"Location": f"/item/{item.id}"}
    )


@app.get("/item")
async def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    q = select(Item)
    if not show_deleted:
        q = q.where(Item.deleted == False)
    if min_price is not None:
        q = q.where(Item.price >= min_price)
    if max_price is not None:
        q = q.where(Item.price <= max_price)
    q = q.offset(offset).limit(limit)
    result = await db.execute(q)
    items_list = result.scalars().all()
    return [it.to_json() for it in items_list]


@app.put("/item/{id}")
async def recreate_item(id: int, item_dto: PutItemDTO, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.id == id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    item.name = item_dto.name
    item.price = item_dto.price
    item.deleted = item_dto.deleted or False

    await db.commit()
    await db.refresh(item)
    
    return JSONResponse(
        status_code=200,
        content=item.to_json(),
        headers={"Location": f"/item/{item.id}"}
    )


@app.patch("/item/{id}")
async def update_item(id: int, item_dto: PatchItemDTO, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.id == id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    if item.deleted:
        return JSONResponse(status_code=304, content=item.to_json())
    if item_dto.name is not None:
        item.name = item_dto.name
    if item_dto.price is not None:
        item.price = item_dto.price
    await db.commit()
    await db.refresh(item)
    return JSONResponse(
        status_code=200,
        content={k: v for k, v in vars(item).items() if not k.startswith("_")},
        headers={"Location": f"/item/{item.id}"}
    )


@app.delete("/item/{id}", status_code=200)
async def delete_item(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Item).where(Item.id == id))
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    item.deleted = True
    await db.commit()
    return {"message": "Item deleted"}
