from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from .schemas import *
from .services import ProductManager, BasketManager
from .data.db_setup import get_database_session
import json
from fastapi.responses import Response

basket_router = APIRouter(prefix="/baskets", tags=["baskets"])
product_router = APIRouter(prefix="/products", tags=["products"])

@basket_router.post("", status_code=201)
def create_new_basket(db: Session = Depends(get_database_session)):
    manager = BasketManager(db)
    basket_data = manager.create_basket()
    return Response(
        content=json.dumps(basket_data),
        media_type="application/json",
        headers={"Location": f"/baskets/{basket_data['id']}"},
        status_code=201
    )

@basket_router.get("/{basket_id}", response_model=BasketInfo)
def retrieve_basket(basket_id: int, db: Session = Depends(get_database_session)):
    manager = BasketManager(db)
    return manager.get_basket_details(basket_id)

@basket_router.get("", response_model=List[BasketInfo])
def list_baskets(
    skip: int = 0, 
    limit: int = 10,
    min_total: Optional[float] = None,
    max_total: Optional[float] = None,
    min_items: Optional[int] = None,
    max_items: Optional[int] = None,
    db: Session = Depends(get_database_session)
):
    if skip < 0 or limit <= 0:
        raise HTTPException(status_code=422, detail="Invalid pagination parameters")
    manager = BasketManager(db)
    return manager.get_all_baskets(skip, limit, min_total, max_total, min_items, max_items)

@basket_router.post("/{basket_id}/products/{product_id}")
def add_product_to_basket(basket_id: int, product_id: int, db: Session = Depends(get_database_session)):
    manager = BasketManager(db)
    manager.add_to_basket(basket_id, product_id)
    return {"message": "Product added to basket"}

@product_router.post("", response_model=ProductInfo, status_code=201)
def create_new_product(product: ProductCreate, db: Session = Depends(get_database_session)):
    manager = ProductManager(db)
    return manager.add_product(product)

@product_router.get("/{product_id}", response_model=ProductInfo)
def get_single_product(product_id: int, db: Session = Depends(get_database_session)):
    manager = ProductManager(db)
    return manager.get_product(product_id)

@product_router.get("", response_model=List[ProductInfo])
def list_products(
    skip: int = 0, 
    limit: int = 10,
    min_cost: Optional[float] = None,
    max_cost: Optional[float] = None,
    include_removed: bool = False,
    db: Session = Depends(get_database_session)
):
    if skip < 0 or limit <= 0:
        raise HTTPException(status_code=422, detail="Invalid pagination parameters")
    manager = ProductManager(db)
    return manager.get_products_list(skip, limit, min_cost, max_cost, include_removed)

@product_router.put("/{product_id}", response_model=ProductInfo)
def replace_product(product_id: int, product: ProductCreate, db: Session = Depends(get_database_session)):
    manager = ProductManager(db)
    return manager.update_product_full(product_id, product)

@product_router.patch("/{product_id}")
def modify_product(product_id: int, modifications: Dict[str, Any] = Body(...), db: Session = Depends(get_database_session)):
    manager = ProductManager(db)
    return manager.update_product_partial(product_id, modifications)

@product_router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_database_session)):
    manager = ProductManager(db)
    manager.remove_product(product_id)
    return {"message": "Product marked as removed"}

# Эндпоинты для демонстрации уровней изоляции
@product_router.get("/isolation/{test_type}/{product_id}")
def test_isolation_levels(
        test_type: str,
        product_id: int,
        db: Session = Depends(get_database_session)
):
    manager = BasketManager(db)

    if test_type == "dirty_read":
        return {"Dirty Read Test": manager.demonstrate_dirty_read(product_id)}
    elif test_type == "non_repeatable":
        return {"Non-repeatable Read Test": manager.demonstrate_non_repeatable_read(product_id)}
    elif test_type == "phantom":
        return {"Phantom Read Test": manager.demonstrate_phantom_read(100.0)}

    raise HTTPException(status_code=400, detail="test_type must be: dirty_read | non_repeatable | phantom")

@product_router.get("/isolation/info")
def isolation_info():
    return {
        "Dirty Read": "READ UNCOMMITTED - Possible",
        "No Dirty Read": "READ COMMITTED - Not possible",
        "Non-repeatable Read": "READ COMMITTED - Possible",
        "No Non-repeatable": "REPEATABLE READ - Not possible",
        "Phantom Read": "REPEATABLE READ - Possible",
        "No Phantom Read": "SERIALIZABLE - Not possible"
    }
