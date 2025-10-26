from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from shop_api.database import get_db
from shop_api.database.schemas import UserCreate, UserResponse, ProductCreate, ProductResponse, OrderCreate, OrderResponse
from shop_api.database.crud import (
    get_user, get_users, create_user, update_user, delete_user,
    get_product, get_products, create_product, update_product, delete_product,
    get_order, get_orders, create_order, update_order, delete_order
)

router = APIRouter()


@router.post("/users/", response_model=UserResponse, status_code=201)
def create_user_endpoint(user: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user)


@router.get("/users/", response_model=List[UserResponse])
def get_users_endpoint(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return get_users(db, skip=skip, limit=limit)


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    db_user = get_user(db, user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user_endpoint(user_id: int, user: UserCreate, db: Session = Depends(get_db)):
    db_user = update_user(db, user_id, user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.delete("/users/{user_id}")
def delete_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    if not delete_user(db, user_id):
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted"}


@router.post("/products/", response_model=ProductResponse, status_code=201)
def create_product_endpoint(product: ProductCreate, db: Session = Depends(get_db)):
    return create_product(db, product)


@router.get("/products/", response_model=List[ProductResponse])
def get_products_endpoint(
    skip: int = 0,
    limit: int = 100,
    min_price: float = None,
    max_price: float = None,
    in_stock: bool = None,
    db: Session = Depends(get_db)
):
    return get_products(db, skip=skip, limit=limit, min_price=min_price, max_price=max_price, in_stock=in_stock)


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product_endpoint(product_id: int, db: Session = Depends(get_db)):
    db_product = get_product(db, product_id)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product_endpoint(product_id: int, product: ProductCreate, db: Session = Depends(get_db)):
    db_product = update_product(db, product_id, product)
    if db_product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return db_product


@router.delete("/products/{product_id}")
def delete_product_endpoint(product_id: int, db: Session = Depends(get_db)):
    if not delete_product(db, product_id):
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted"}


@router.post("/orders/", response_model=OrderResponse, status_code=201)
def create_order_endpoint(order: OrderCreate, db: Session = Depends(get_db)):
    try:
        return create_order(db, order)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/orders/", response_model=List[OrderResponse])
def get_orders_endpoint(
    skip: int = 0,
    limit: int = 100,
    user_id: int = None,
    product_id: int = None,
    status: str = None,
    db: Session = Depends(get_db)
):
    return get_orders(db, skip=skip, limit=limit, user_id=user_id, product_id=product_id, status=status)


@router.get("/orders/{order_id}", response_model=OrderResponse)
def get_order_endpoint(order_id: int, db: Session = Depends(get_db)):
    db_order = get_order(db, order_id)
    if db_order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return db_order


@router.put("/orders/{order_id}", response_model=OrderResponse)
def update_order_endpoint(order_id: int, order: OrderCreate, db: Session = Depends(get_db)):
    try:
        db_order = update_order(db, order_id, order)
        if db_order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        return db_order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/orders/{order_id}")
def delete_order_endpoint(order_id: int, db: Session = Depends(get_db)):
    if not delete_order(db, order_id):
        raise HTTPException(status_code=404, detail="Order not found")
    return {"message": "Order deleted"}
