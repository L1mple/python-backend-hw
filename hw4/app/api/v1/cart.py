from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

import app.crud.cart as crud_cart
from app.core.mongo import get_mongo

# Роутер корзин
router = APIRouter(tags=["cart"])


@router.post("/cart")
async def create_cart(mongo=Depends(get_mongo)):
    cart = await crud_cart.create_cart(mongo)
    return JSONResponse(
        content=cart.model_dump(),
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/cart/{cart.id}"},
    )


@router.get("/cart/{cart_id}")
async def get_cart_by_id(cart_id: int, mongo=Depends(get_mongo)):
    cart = await crud_cart.get_cart_by_id(mongo, cart_id)
    if cart is None:
        return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
    else:
        return JSONResponse(content=cart.model_dump(), status_code=status.HTTP_200_OK)


@router.get("/cart")
async def get_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: float = None,
    max_price: float = None,
    min_quantity: int = None,
    max_quantity: int = None,
    mongo=Depends(get_mongo),
):
    carts, code = await crud_cart.get_carts(mongo, offset, limit, min_price, max_price, min_quantity, max_quantity)
    if code == 422:
        return JSONResponse(content=[], status_code=status.HTTP_422_UNPROCESSABLE_CONTENT)
    return JSONResponse(content=[cart.model_dump() for cart in carts], status_code=status.HTTP_200_OK)


@router.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: int, item_id: int, mongo=Depends(get_mongo)):
    cart, code = await crud_cart.add_item_to_cart(mongo, cart_id, item_id)
    if code == 404:
        return JSONResponse(content={}, status_code=status.HTTP_404_NOT_FOUND)
    return JSONResponse(
        content={
            "id": cart.id,
            "price": cart.price,
            "items": [item.model_dump() for item in cart.items],
        },
        status_code=status.HTTP_200_OK,
    )