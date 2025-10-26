from http import HTTPStatus
from typing import List, Optional
from prometheus_fastapi_instrumentator import Instrumentator

from fastapi import FastAPI, HTTPException, Query, Response, Depends
from sqlalchemy import select, and_, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from .db import (
    SessionLocal,
    Item as ItemORM,
    Cart as CartORM,
    ItemInCart as ItemInCartORM,
)
from .schemas import (
    ItemCreate, ItemUpdate, ItemPatch, ItemOut,
    CartOut, ItemInCartOut,
)

app = FastAPI(title="Shop API")

Instrumentator().instrument(app).expose(app)

# Dependency that provides a DB session per request
async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session



@app.post("/item", response_model=ItemOut, status_code=HTTPStatus.CREATED)
async def create_item(
    data: ItemCreate,
    session: AsyncSession = Depends(get_session),
):
    obj = ItemORM(name=data.name, price=data.price, deleted=False)

    session.add(obj)

    await session.commit()

    await session.refresh(obj)

    return ItemOut.model_validate(obj, from_attributes=True)


@app.get("/item/{id}", response_model=ItemOut)
async def get_item(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        select(ItemORM).where(ItemORM.id == id, ItemORM.deleted == False)
    )
    obj = res.scalar_one_or_none()

    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")

    return ItemOut.model_validate(obj, from_attributes=True)


@app.get("/item", response_model=List[ItemOut])
async def get_items_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    stmt = select(ItemORM)

    conditions = []
    if not show_deleted:
        conditions.append(ItemORM.deleted == False)
    if min_price is not None:
        conditions.append(ItemORM.price >= min_price)
    if max_price is not None:
        conditions.append(ItemORM.price <= max_price)

    if conditions:
        stmt = stmt.where(and_(*conditions))

    stmt = stmt.offset(offset).limit(limit)

    result = await session.execute(stmt)
    items = result.scalars().all()

    return [ItemOut.model_validate(i, from_attributes=True) for i in items]


@app.put("/item/{id}", response_model=ItemOut)
async def update_item(
    id: int,
    params: ItemUpdate,
    session: AsyncSession = Depends(get_session),
):
    obj = await session.get(ItemORM, id)
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")

    obj.name = params.name
    obj.price = params.price
    obj.deleted = params.deleted or False

    await session.commit()
    await session.refresh(obj)
    return ItemOut.model_validate(obj, from_attributes=True)

@app.patch("/item/{id}", response_model=ItemOut)
async def patch_item(
    id: int,
    params: ItemPatch,
    session: AsyncSession = Depends(get_session),
):
    obj = await session.get(ItemORM, id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Item not found")

    if obj.deleted:
        return Response(status_code=304)

    data = params.model_dump(exclude_unset=True)

    if not data:
        return ItemOut.model_validate(obj, from_attributes=True)

    for field, value in data.items():
        setattr(obj, field, value)

    await session.commit()
    await session.refresh(obj)

    return ItemOut.model_validate(obj, from_attributes=True)


@app.delete("/item/{id}")
async def delete_item(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    res = await session.get(ItemORM, id)
    if res is None:
        return

    res.deleted = True
    await session.commit()
    return


@app.post("/cart", response_model=CartOut, status_code=HTTPStatus.CREATED)
async def create_cart( session: AsyncSession = Depends(get_session), ):
    obj = CartORM()

    session.add(obj)

    await session.commit()

    await session.refresh(obj)

    return CartOut(id=obj.id, items=[], price=0.0)


@app.get("/cart/{id}", response_model=CartOut)
async def get_cart(
    id: int,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(select(CartORM).where(CartORM.id == id))
    cart = res.scalar_one_or_none()
    if not cart:
        raise HTTPException(status_code=404, detail="Cart not found")

    ci, it = ItemInCartORM, ItemORM
    res = await session.execute(
        select(ci.item_id, it.name, ci.quantity, it.deleted)
        .join(it, it.id == ci.item_id)
        .where(ci.cart_id == id)
    )
    rows = res.all()

    items = [
        ItemInCartOut(
            id=item_id,
            name=name,
            quantity=quantity,
            available=not deleted_flag,
        )
        for (item_id, name, quantity, deleted_flag) in rows
    ]

    total_q = await session.execute(
        select(func.coalesce(func.sum(ci.quantity * it.price), 0))
        .join(it, it.id == ci.item_id)
        .where(ci.cart_id == id, it.deleted == False)
    )
    total = float(total_q.scalar_one())

    return CartOut(id=id, items=items, price=total)


@app.get("/cart", response_model=List[CartOut])
async def get_carts_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
    session: AsyncSession = Depends(get_session),
):
    c, ci, it = CartORM, ItemInCartORM, ItemORM

    agg = (
        select(
            c.id.label("cart_id"),
            func.coalesce(func.sum(ci.quantity), 0).label("qty"),
            func.coalesce(
                func.sum((ci.quantity * it.price).filter(it.deleted == False)),
                0
            ).label("price"),
        )
        .select_from(c)
        .join(ci, ci.cart_id == c.id, isouter=True)
        .join(it, it.id == ci.item_id, isouter=True)
        .group_by(c.id)
    )

    sub = agg.subquery()

    stmt = select(sub.c.cart_id, sub.c.qty, sub.c.price)

    if min_price is not None:
        stmt = stmt.where(sub.c.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(sub.c.price <= max_price)
    if min_quantity is not None:
        stmt = stmt.where(sub.c.qty >= min_quantity)
    if max_quantity is not None:
        stmt = stmt.where(sub.c.qty <= max_quantity)

    stmt = stmt.offset(offset).limit(limit)

    res = await session.execute(stmt)
    rows = res.mappings().all()

    return [
        CartOut(
            id=row["cart_id"],
            items=[],
            price=float(row["price"]),
        )
        for row in rows
    ]

@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(
    cart_id: int,
    item_id: int,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        select(ItemORM).where(ItemORM.id == item_id, ItemORM.deleted == False)
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Item not found")

    res = await session.execute(
        select(CartORM).where(CartORM.id == cart_id)
    )
    obj = res.scalar_one_or_none()
    if not obj:
        raise HTTPException(status_code=404, detail="Cart not found")

    stmt = pg_insert(ItemInCartORM).values(
        cart_id=cart_id,
        item_id=item_id,
        quantity=1,
    ).on_conflict_do_update(
        index_elements=[ItemInCartORM.cart_id, ItemInCartORM.item_id],
        set_={"quantity": ItemInCartORM.quantity + 1},
    )
    await session.execute(stmt)
    await session.commit()




















