from fastapi import FastAPI, HTTPException, Query, status, Response
from typing import List, Optional
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from .schemas import ItemIn, ItemOut, ItemPatch, CartItemOut, CartOut
from .database import SessionLocal, engine
from .models import Base, Item, Cart, CartItem
from sqlalchemy.orm import joinedload

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

Base.metadata.create_all(bind=engine)


def get_item_or_404(db: Session, item_id: int, allow_deleted: bool = False) -> Item:
    item = db.get(Item, item_id)
    if not item or (item.deleted and not allow_deleted):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Item not found")
    return item

def get_cart_or_404(db: Session, cart_id: int) -> Cart:
    cart = db.query(Cart).options(
        joinedload(Cart.items).joinedload(CartItem.item)
    ).filter(Cart.id == cart_id).first()
    if not cart:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Cart not found")
    return cart


def cart_to_out(db: Session, cart: Cart) -> CartOut:
    out_items = []
    total_price = 0.0

    for cart_item in cart.items:
        item = cart_item.item
        out_items.append(CartItemOut(
            id=item.id,
            name=item.name,
            quantity=cart_item.quantity,
            available=not item.deleted
        ))
        if not item.deleted:
            total_price += item.price * cart_item.quantity

    return CartOut(
        id=cart.id,
        items=out_items,
        price=total_price
    )

@app.post("/cart", status_code=status.HTTP_201_CREATED)
def post_cart(response: Response):
    db = SessionLocal()
    try:
        cart = Cart()
        db.add(cart)
        db.commit()
        response.headers["location"] = f"/cart/{cart.id}"
        return {"id": cart.id}
    finally:
        db.close()

@app.get("/cart/{cart_id}", response_model=CartOut)
def get_cart(cart_id: int):
    db = SessionLocal()
    try:
        cart = get_cart_or_404(db, cart_id)
        return cart_to_out(db, cart)
    finally:
        db.close()


@app.post("/cart/{cart_id}/add/{item_id}")
def cart_add(cart_id: int, item_id: int):
    db = SessionLocal()
    try:
        cart = get_cart_or_404(db, cart_id)
        item = get_item_or_404(db, item_id)

        cart_item = next((ci for ci in cart.items if ci.item_id == item_id), None)

        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
            db.add(cart_item)

        db.commit()
        return {"cart_id": cart_id, "item_id": item_id, "quantity": cart_item.quantity}
    finally:
        db.close()


@app.post("/item", response_model=ItemOut, status_code=status.HTTP_201_CREATED)
def add_item(item: ItemIn, response: Response):
    db = SessionLocal()
    try:
        new_item = Item(name=item.name, price=item.price)
        db.add(new_item)
        db.commit()
        db.refresh(new_item)
        response.headers["location"] = f"/item/{new_item.id}"
        return new_item
    finally:
        db.close()

@app.get("/item/{item_id}", response_model=ItemOut)
def get_item(item_id: int):
    db = SessionLocal()
    try:
        item = get_item_or_404(db, item_id)
        return item
    finally:
        db.close()

@app.get("/item", response_model=List[ItemOut])
def get_item_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = Query(False),
):
    db = SessionLocal()
    try:
        query = db.query(Item)

        if not show_deleted:
            query = query.filter(Item.deleted == False)

        if min_price is not None:
            query = query.filter(Item.price >= min_price)

        if max_price is not None:
            query = query.filter(Item.price <= max_price)

        items = query.offset(offset).limit(limit).all()
        return items
    finally:
        db.close()

@app.put("/item/{item_id}", response_model=ItemOut)
def replace_item(item_id: int, item_in: ItemIn):
    db = SessionLocal()
    try:
        item = get_item_or_404(db, item_id)
        item.name = item_in.name
        item.price = item_in.price
        db.commit()
        db.refresh(item)
        return item
    finally:
        db.close()

@app.patch("/item/{item_id}", response_model=ItemOut)
def patch_item(item_id: int, item_patch: ItemPatch):
    db = SessionLocal()
    try:
        item = get_item_or_404(db, item_id)

        if item.deleted:
            return Response(status_code=status.HTTP_304_NOT_MODIFIED)

        if item_patch.name is not None:
            item.name = item_patch.name

        if item_patch.price is not None:
            item.price = item_patch.price

        db.commit()
        db.refresh(item)
        return item
    finally:
        db.close()

@app.delete("/item/{item_id}", response_model=ItemOut)
def delete_item(item_id: int):
    db = SessionLocal()
    try:
        item = db.get(Item, item_id)
        if item is None:
            return Response(status_code=status.HTTP_200_OK)

        item.deleted = True
        db.commit()
        db.refresh(item)
        return item
    finally:
        db.close()

@app.get("/cart", response_model=List[CartOut])
def get_cart_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    db = SessionLocal()
    try:
        query = db.query(Cart)

        carts = query.offset(offset).limit(limit).all()

        result = []
        for cart in carts:
            cart_out = cart_to_out(db, cart)

            total_q = sum(i.quantity for i in cart_out.items if i.available)

            if min_price is not None and cart_out.price < min_price:
                continue
            if max_price is not None and cart_out.price > max_price:
                continue
            if min_quantity is not None and total_q < min_quantity:
                continue
            if max_quantity is not None and total_q > max_quantity:
                continue

            result.append(cart_out)

        return result
    finally:
        db.close()

@app.get("/check-db")
def check_db():
    db = SessionLocal()
    try:
        items_count = db.query(Item).count()
        carts_count = db.query(Cart).count()
        return {
            "items": items_count,
            "carts": carts_count,
            "cart_items": db.query(CartItem).count()
        }
    finally:
        db.close()

from sqlalchemy import text

@app.on_event("startup")
async def startup():
    print("✅ Application started")
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
            db.commit()
        print("✅ Database connection successful")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
