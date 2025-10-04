from __future__ import annotations

from http import HTTPStatus
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(prefix="/cart", tags=["carts"])


@router.post("", response_model=schemas.CartCreateResponse, status_code=HTTPStatus.CREATED)
def create_cart(response: Response, db: Session = Depends(get_db)):
    """Создание новой корзины"""
    db_cart = models.Cart()
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    response.headers["location"] = f"/cart/{db_cart.id}"
    return db_cart


@router.get("/{cart_id}", response_model=schemas.CartResponse)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    """Получение корзины по ID"""
    cart = db.query(models.Cart).filter(models.Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

    items = []
    total_price = 0.0

    for cart_item in cart.cart_items:
        item = cart_item.item
        items.append(
            schemas.CartItemResponse(
                id=item.id,
                name=item.name,
                quantity=cart_item.quantity,
                available=not item.deleted,
            )
        )
        if not item.deleted:
            total_price += item.price * cart_item.quantity

    return schemas.CartResponse(id=cart.id, items=items, price=total_price)


@router.get("", response_model=list[schemas.CartResponse])
def get_carts(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[Optional[float], Query(ge=0)] = None,
    max_price: Annotated[Optional[float], Query(ge=0)] = None,
    min_quantity: Annotated[Optional[int], Query(ge=0)] = None,
    max_quantity: Annotated[Optional[int], Query(ge=0)] = None,
    db: Session = Depends(get_db),
):
    """Получение списка корзин с фильтрацией"""
    carts = db.query(models.Cart).all()

    cart_responses = []
    for cart in carts:
        items = []
        total_price = 0.0
        total_quantity = 0

        for cart_item in cart.cart_items:
            item = cart_item.item
            items.append(
                schemas.CartItemResponse(
                    id=item.id,
                    name=item.name,
                    quantity=cart_item.quantity,
                    available=not item.deleted,
                )
            )
            if not item.deleted:
                total_price += item.price * cart_item.quantity
            total_quantity += cart_item.quantity

        cart_response = schemas.CartResponse(id=cart.id, items=items, price=total_price)

        # Apply filters
        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        cart_responses.append(cart_response)

    return cart_responses[offset : offset + limit]


@router.post("/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    """Добавление товара в корзину"""
    cart = db.query(models.Cart).filter(models.Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

    item = db.query(models.Item).filter(models.Item.id == item_id).first()
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")

    # Check if item already in cart
    cart_item = (
        db.query(models.CartItem)
        .filter(models.CartItem.cart_id == cart_id, models.CartItem.item_id == item_id)
        .first()
    )

    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = models.CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(cart_item)

    db.commit()
    return {"message": "Item added to cart"}

