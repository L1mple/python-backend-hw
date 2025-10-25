from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from .models import *
from .services import ItemService, CartService
from hw4.hw.shop_api.db.db_init import get_db
import json
from fastapi.responses import Response

cart_router = APIRouter(prefix="/cart", tags=["cart"])
item_router = APIRouter(prefix="/item", tags=["item"])

@cart_router.post("", status_code=201)
def create_cart(db: Session = Depends(get_db)):
    service = CartService(db)
    cart = service.create_cart()
    return Response(
        content=json.dumps(cart),
        media_type="application/json",
        headers={"Location": f"/cart/{cart['id']}"},
        status_code=201
    )

@cart_router.get("/{cart_id}", response_model=CartResponse)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    service = CartService(db)
    return service.get_cart(cart_id)

@cart_router.get("", response_model=List[CartResponse])
def get_carts(
    offset: int = 0, limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    min_quantity: Optional[int] = None,
    max_quantity: Optional[int] = None,
    db: Session = Depends(get_db)
):
    if offset < 0 or limit <= 0: raise HTTPException(422)
    service = CartService(db)
    return service.get_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)

@cart_router.post("/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    service = CartService(db)
    service.add_item_to_cart(cart_id, item_id)
    return {"status": "success"}

@item_router.post("", response_model=ItemResponse, status_code=201)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    service = ItemService(db)
    return service.create_item(item)

@item_router.get("/{item_id}", response_model=ItemResponse)
def get_item(item_id: int, db: Session = Depends(get_db)):
    service = ItemService(db)
    return service.get_item(item_id)

@item_router.get("", response_model=List[ItemResponse])
def get_items(
    offset: int = 0, limit: int = 10,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    show_deleted: bool = False,
    db: Session = Depends(get_db)
):
    if offset < 0 or limit <= 0: raise HTTPException(422)
    service = ItemService(db)
    return service.get_items(offset, limit, min_price, max_price, show_deleted)

@item_router.put("/{item_id}", response_model=ItemResponse)
def replace_item(item_id: int, item: ItemCreate, db: Session = Depends(get_db)):
    service = ItemService(db)
    return service.replace_item(item_id, item)

@item_router.patch("/{item_id}")
def update_item(item_id: int, updates: Dict[str, Any] = Body(...), db: Session = Depends(get_db)):
    service = ItemService(db)
    return service.update_item(item_id, updates)

@item_router.delete("/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    service = ItemService(db)
    service.delete_item(item_id)
    return {"status": "deleted"}


# ✅ ЭНДПОИНТЫ ДЕМОНСТРАЦИИ ИЗОЛЯЦИИ
@item_router.get("/isolation/{isolation_type}/{item_id}")
def demo_isolation(
        isolation_type: str,
        item_id: int,
        db: Session = Depends(get_db)
):
    service = CartService(db)

    if isolation_type == "dirty":
        return {"✅ Dirty Read": service.demo_dirty_read(item_id)}
    elif isolation_type == "non_repeatable":
        return {"✅ Non-repeatable Read": service.demo_non_repeatable_read(item_id)}
    elif isolation_type == "phantom":
        return {"✅ Phantom Read": service.demo_phantom_read(100.0)}

    raise HTTPException(400, "isolation_type: dirty | non_repeatable | phantom")


@item_router.get("/isolation/matrix")
def isolation_matrix(db: Session = Depends(get_db)):
    return {
        "✅ Dirty Read": "READ UNCOMMITTED → Возможен",
        "✅ Нет Dirty Read": "READ COMMITTED → Невозможен",
        "✅ Non-repeatable Read": "READ COMMITTED → Возможен",
        "✅ Нет Non-repeatable": "REPEATABLE READ → Невозможен",
        "✅ Phantom Read": "REPEATABLE READ → Возможен",
        "✅ Нет Phantom Read": "SERIALIZABLE → Невозможен"
    }