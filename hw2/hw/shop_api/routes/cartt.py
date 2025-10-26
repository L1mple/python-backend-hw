from __future__ import annotations

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from ..models import CartCreateResponse, CartListQuery, CartResponse
from ..services import CartService, ItemService
from ..dependencies import get_cart_service

router = APIRouter()


@router.post(
    "",
    response_model=CartCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_cart(cart_service: CartService = Depends(get_cart_service)):
    response = cart_service.create()
    
    # Возвращаем ответ с заголовком location
    return JSONResponse(
        content={"id": response.id},
        status_code=status.HTTP_201_CREATED,
        headers={"location": f"/cart/{response.id}"}
    )


@router.get("/{cart_id}", response_model=CartResponse)
def get_cart(cart_id: int, cart_service: CartService = Depends(get_cart_service)) -> CartResponse:
    return cart_service.get(cart_id)


@router.get("", response_model=list[CartResponse])
def list_carts(
    query: CartListQuery = Depends(),
    cart_service: CartService = Depends(get_cart_service),
) -> list[CartResponse]:
    return cart_service.list(query)


@router.post("/{cart_id}/add/{item_id}", response_model=CartResponse)
def add_item_to_cart(
    cart_id: int,
    item_id: int,
    cart_service: CartService = Depends(get_cart_service),
) -> CartResponse:
    return cart_service.add_item(cart_id, item_id)