from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from shop_api.core.schemas import CartView
from shop_api.core.db import get_session
from shop_api.core.models import Cart
from shop_api.core import storage as crud

router = APIRouter(prefix="/cart", tags=["cart"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_cart(response: Response, session: AsyncSession = Depends(get_session)):
    cart_id = await crud.create_cart(session)
    await session.commit()
    response.headers["Location"] = f"/cart/{cart_id}"
    return {"id": cart_id}


@router.get("/{cart_id}", response_model=CartView)
async def get_cart(cart_id: int, session: AsyncSession = Depends(get_session)) -> CartView:
    return await crud.build_cart_view(session, cart_id)


@router.get("", response_model=List[CartView])
async def list_carts(
    offset: int = Query(0, ge=0, description="Смещение по списку (offset)"),
    limit: int = Query(10, gt=0, description="Лимит количества (limit)"),
    min_price: Optional[float] = Query(
        None, ge=0.0, description="Мин. сумма корзины (включительно)"
    ),
    max_price: Optional[float] = Query(
        None, ge=0.0, description="Макс. сумма корзины (включительно)"
    ),
    min_quantity: Optional[int] = Query(
        None, ge=0, description="Мин. общее число товаров (включительно)"
    ),
    max_quantity: Optional[int] = Query(
        None, ge=0, description="Макс. общее число товаров (включительно)"
    ),
    session: AsyncSession = Depends(get_session),
) -> List[CartView]:
    # First gather candidate cart ids
    res = await session.execute(select(Cart.id))
    ids = [row[0] for row in res.all()]

    views: List[CartView] = []
    for cid in ids:
        v = await crud.build_cart_view(session, cid)

        if min_price is not None and v.price < min_price:
            continue
        if max_price is not None and v.price > max_price:
            continue

        qsum = sum(it.quantity for it in v.items)
        if min_quantity is not None and qsum < min_quantity:
            continue
        if max_quantity is not None and qsum > max_quantity:
            continue

        views.append(v)

    return views[offset : offset + limit]


@router.post("/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int, session: AsyncSession = Depends(get_session)):
    await crud.add_to_cart(session, cart_id, item_id)
    await session.commit()
    return {"ok": True}
