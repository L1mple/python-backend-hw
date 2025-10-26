from fastapi import APIRouter, status, Response, Query, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from src.crud import crud_cart
from src.db import get_db
from src.schemas import (
    CartResponse,
    CartCreateResponse,
    Msg
)


router = APIRouter()


@router.post(
    path="",
    response_model=CartCreateResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_cart(
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    new_cart = await crud_cart.create(db)
    cart_id = new_cart.id
    response.headers["Location"] = f"/carts/{cart_id}"
    return CartCreateResponse(id=cart_id)


@router.get(
    path="/{id}",
    response_model=CartResponse
)
async def get_cart(
    id: UUID,
    db: AsyncSession = Depends(get_db)
):
    cart = await crud_cart.get_cart_with_items(db=db, id=id)
    if cart is None:
        return JSONResponse(
            content=Msg(msg="Корзина не найдена").model_dump(),
            status_code=404
        )
    return cart


@router.get(
    path="",
    response_model=List[CartResponse]
)
async def get_list_carts(
        offset: Optional[int] = Query(None, ge=0),
        limit: Optional[int] = Query(None, ge=1),
        min_price: Optional[float] = Query(None, ge=0.0),
        max_price: Optional[float] = Query(None, ge=0.0),
        min_quantity: Optional[int] = Query(None, ge=0),
        max_quantity: Optional[int] = Query(None, ge=0),
        db: AsyncSession = Depends(get_db)
):
    carts = await crud_cart.get_carts_with_filters(
        db=db,
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )

    return carts


@router.post(
    path="/{cart_id}/add/{item_id}",
    response_model=Msg
)
async def add_item_to_cart_endpoint(
    cart_id: UUID,
    item_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    cart = await crud_cart.add_item_to_cart(
        db=db,
        cart_id=cart_id,
        item_id=item_id
    )

    if not cart:
        return JSONResponse(
            content=Msg(msg="Ничего не найдено").model_dump(),
            status_code=404
        )

    return JSONResponse(
            content=Msg(msg=f"Айтем {item_id} успешно добавлен в корзину {cart_id}").model_dump(),
            status_code=200
        )