from fastapi import APIRouter, Body, status, HTTPException, Response, Request
from typing import Optional, List, Dict, Any
from .models import ItemCreate, ItemResponse, CartResponse, CartItemResponse
from .services import CartService, ItemService
from fastapi.encoders import jsonable_encoder
import json

cart_router = APIRouter(prefix="/cart", tags=["cart"])
item_router = APIRouter(prefix="/item", tags=["item"])

cart_service = CartService()
item_service = ItemService()

@cart_router.post("", status_code=status.HTTP_201_CREATED)
def create_cart(request: Request):
    cart = cart_service.create_cart()
    response_data = {"id": cart["id"]}
    return Response(
        content=json.dumps(response_data),
        media_type="application/json",
        headers={"Location": f"/cart/{cart['id']}"},
        status_code=status.HTTP_201_CREATED
    )

@cart_router.get("/{cart_id}", response_model=CartResponse, name="get_cart")
def get_cart(cart_id: int) -> CartResponse:
    return cart_service.get_cart(cart_id)

@cart_router.get("", response_model=List[CartResponse])
def get_carts(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
) -> List[CartResponse]:
    if offset < 0 or limit <= 0 or (min_price is not None and min_price < 0) or (max_price is not None and max_price < 0) or (min_quantity is not None and min_quantity < 0) or (max_quantity is not None and max_quantity < 0):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return cart_service.get_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)

@cart_router.post("/{cart_id}/add/{item_id}", status_code=status.HTTP_200_OK)
def add_item_to_cart(cart_id: int, item_id: int) -> Dict[str, str]:
    cart_service.add_item_to_cart(cart_id, item_id, item_service)
    return {"status": "success"}

@item_router.post("", status_code=status.HTTP_201_CREATED, response_model=ItemResponse)
def create_item(item: ItemCreate) -> ItemResponse:
    return item_service.create_item(item)

@item_router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int) -> ItemResponse:
    return item_service.get_item(item_id)

@item_router.get("", response_model=List[ItemResponse])
def get_items(
    offset: int = 0,
    limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
) -> List[ItemResponse]:
    if offset < 0 or limit <= 0 or (min_price is not None and min_price < 0) or (max_price is not None and max_price < 0):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return item_service.get_items(offset, limit, min_price, max_price, show_deleted)

@item_router.put("/{item_id}", response_model=ItemResponse)
def replace_item(item_id: int, item: ItemCreate) -> ItemResponse:
    return item_service.replace_item(item_id, item)

@item_router.patch("/{item_id}")
def update_item(item_id: int, updates: Dict[str, Any] = Body(...)):
    if any(key not in ["name", "price"] for key in updates.keys()):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    return item_service.update_item(item_id, updates)

@item_router.delete("/{item_id}", status_code=status.HTTP_200_OK)
def delete_item(item_id: int) -> Dict[str, str]:
    item_service.delete_item(item_id)
    return {"status": "deleted"}
