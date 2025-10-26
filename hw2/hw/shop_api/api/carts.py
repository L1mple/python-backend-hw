from __future__ import annotations
from http import HTTPStatus
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from sqlalchemy.orm import Session

from shop_api.core import crud, schemas
from shop_api.core.database import get_db

router = APIRouter(tags=["carts"])


@router.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response, db: Session = Depends(get_db)):
    cart = crud.create_cart(db)
    response.headers["Location"] = f"/cart/{cart.id}"
    return {"id": cart.id}


@router.get("/cart/{cart_id}", response_model=schemas.CartOut)
def get_cart(cart_id: int = Path(ge=1), db: Session = Depends(get_db)):
    cart = db.query(crud.models.CartDB).filter_by(id=cart_id).first()
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

    items_out: list[schemas.CartOutItem] = []
    total_price = 0.0

    for cart_item in cart.items:
        item = cart_item.item
        if item is None:
            items_out.append(
                schemas.CartOutItem(
                    id=cart_item.item_id,
                    name="Unknown",
                    quantity=cart_item.quantity,
                    available=False,
                )
            )
        else:
            items_out.append(
                schemas.CartOutItem(
                    id=item.id,
                    name=item.name,
                    quantity=cart_item.quantity,
                    available=not item.deleted,
                )
            )
            if not item.deleted:
                total_price += item.price * cart_item.quantity

    return schemas.CartOut(id=cart.id, items=items_out, price=total_price)


@router.post("/cart/{cart_id}/add/{item_id}", status_code=HTTPStatus.OK)
def add_item_to_cart(
    cart_id: int = Path(ge=1),
    item_id: int = Path(ge=1),
    db: Session = Depends(get_db),
):
    cart = crud.add_item_to_cart(db, cart_id, item_id)
    if cart is None:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart or item not found")
    return {"status": "ok"}


@router.get("/cart", response_model=list[schemas.CartOut])
def list_carts(
    db: Session = Depends(get_db),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1),
    min_price: float | None = Query(default=None, ge=0),
    max_price: float | None = Query(default=None, ge=0),
    min_quantity: int | None = Query(default=None, ge=0),
    max_quantity: int | None = Query(default=None, ge=0),
):
    carts = db.query(crud.models.CartDB).offset(offset).limit(limit).all()
    result: list[schemas.CartOut] = []

    for cart in carts:
        items_out: list[schemas.CartOutItem] = []
        total_price = 0.0

        for ci in cart.items:
            item = ci.item
            if item:
                available = not item.deleted
                name = item.name
                if available:
                    total_price += item.price * ci.quantity
            else:
                name = "Unknown"
                available = False

            items_out.append(
                schemas.CartOutItem(
                    id=ci.item_id,
                    name=name,
                    quantity=ci.quantity,
                    available=available,
                )
            )

        result.append(schemas.CartOut(id=cart.id, items=items_out, price=total_price))

    if min_price is not None:
        result = [c for c in result if c.price >= min_price]
    if max_price is not None:
        result = [c for c in result if c.price <= max_price]

    def sum_quantity(cart_out: schemas.CartOut) -> int:
        return sum(i.quantity for i in cart_out.items)

    if min_quantity is not None:
        result = [c for c in result if sum_quantity(c) >= min_quantity]
    if max_quantity is not None:
        result = [c for c in result if sum_quantity(c) <= max_quantity]

    return result