from http import HTTPStatus
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Response, Depends
from pydantic import BaseModel, NonNegativeInt, PositiveInt, PositiveFloat, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database import get_db
from models import ItemORM, CartORM, CartItemORM

app = FastAPI(title="Shop API")

class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False

class ItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    price: PositiveFloat

class ItemPut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    price: PositiveFloat

class ItemPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = None
    price: Optional[PositiveFloat] = None

def _cart_total_price(db: Session, cid: int) -> float:
    q = (
        select(func.coalesce(func.sum(ItemORM.price * CartItemORM.quantity), 0))
        .join(CartItemORM, CartItemORM.item_id == ItemORM.id)
        .where(CartItemORM.cart_id == cid, ItemORM.deleted == False)  # noqa: E712
    )
    return float(db.execute(q).scalar_one())

def _cart_items_repr(db: Session, cid: int) -> List[dict]:
    q = select(CartItemORM.item_id, CartItemORM.quantity).where(CartItemORM.cart_id == cid)
    return [{"id": r.item_id, "quantity": r.quantity} for r in db.execute(q).all()]

@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(body: ItemCreate, db: Session = Depends(get_db)):
    row = ItemORM(name=body.name, price=float(body.price))
    db.add(row); db.commit(); db.refresh(row)
    return {"id": row.id, "name": row.name, "price": float(row.price), "deleted": row.deleted}

@app.get("/item/{id}")
def get_item(id: int, db: Session = Depends(get_db)):
    row = db.get(ItemORM, id)
    if row is None or row.deleted:
        raise HTTPException(HTTPStatus.NOT_FOUND)
    return {"id": row.id, "name": row.name, "price": float(row.price), "deleted": row.deleted}

@app.get("/item")
def list_items(
    offset: NonNegativeInt = 0,
    limit: Optional[PositiveInt] = None,
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    show_deleted: bool = False,
    db: Session = Depends(get_db),
):
    q = select(ItemORM)
    if min_price is not None: q = q.where(ItemORM.price >= float(min_price))
    if max_price is not None: q = q.where(ItemORM.price <= float(max_price))
    q = q.order_by(ItemORM.id).offset(offset)
    if limit is not None: q = q.limit(limit)
    out = []
    for row in db.execute(q).scalars():
        if show_deleted or not row.deleted:
            out.append({"id": row.id, "name": row.name, "price": float(row.price), "deleted": row.deleted})
    return out

@app.put("/item/{id}")
def put_item(id: int, body: ItemPut, db: Session = Depends(get_db)):
    row = db.get(ItemORM, id)
    if row is None or row.deleted:
        raise HTTPException(HTTPStatus.NOT_MODIFIED)
    row.name = body.name
    row.price = float(body.price)
    db.commit(); db.refresh(row)
    return {"id": row.id, "name": row.name, "price": float(row.price), "deleted": row.deleted}

@app.patch("/item/{id}")
def patch_item(id: int, body: ItemPatch, db: Session = Depends(get_db)):
    row = db.get(ItemORM, id)
    if row is None or row.deleted:
        raise HTTPException(HTTPStatus.NOT_MODIFIED)
    updates = body.model_dump(exclude_unset=True)
    if "name" in updates: row.name = updates["name"]
    if "price" in updates: row.price = float(updates["price"])
    db.commit(); db.refresh(row)
    return {"id": row.id, "name": row.name, "price": float(row.price), "deleted": row.deleted}

@app.delete("/item/{id}")
def delete_item(id: int, db: Session = Depends(get_db)):
    row = db.get(ItemORM, id)
    if row is None: return Response("")
    if not row.deleted:
        row.deleted = True; db.commit()
    return Response("")

@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response, db: Session = Depends(get_db)):
    cart = CartORM(); db.add(cart); db.commit(); db.refresh(cart)
    response.headers["Location"] = f"/cart/{cart.id}"
    return {"id": cart.id}

@app.get("/cart/{id}")
def get_cart(id: int, db: Session = Depends(get_db)):
    cart = db.get(CartORM, id)
    if cart is None: raise HTTPException(HTTPStatus.NOT_FOUND)
    return {"id": id, "items": _cart_items_repr(db, id), "price": _cart_total_price(db, id)}

@app.post("/cart/{id}/add/{item_id}")
def add_item_to_cart(id: int, item_id: int, db: Session = Depends(get_db)):
    if db.get(CartORM, id) is None: raise HTTPException(HTTPStatus.NOT_FOUND)
    # main.py (add_item_to_cart)
    ci = db.get(CartItemORM, (id, item_id))  # вместо dict
    if ci is None:
        ci = CartItemORM(cart_id=id, item_id=item_id, quantity=1); db.add(ci)
    else:
        ci.quantity += 1
    db.commit()
    return {"id": id, "items": _cart_items_repr(db, id), "price": _cart_total_price(db, id)}

@app.get("/cart")
def list_carts(
    offset: NonNegativeInt = 0,
    limit: Optional[PositiveInt] = None,
    min_price: Optional[float] = Query(default=None, ge=0.0),
    max_price: Optional[float] = Query(default=None, ge=0.0),
    min_quantity: Optional[NonNegativeInt] = None,
    max_quantity: Optional[NonNegativeInt] = None,
    db: Session = Depends(get_db),
):
    ids = [r for r in db.execute(select(CartORM.id).order_by(CartORM.id)).scalars().all()]
    filtered = []
    for cid in ids:
        price = _cart_total_price(db, cid)
        if min_price is not None and price < float(min_price): continue
        if max_price is not None and price > float(max_price): continue
        filtered.append(cid)
    if min_quantity is not None or max_quantity is not None:
        agg = 0; constrained = []
        for cid in filtered:
            q = select(func.coalesce(func.sum(CartItemORM.quantity), 0)).where(CartItemORM.cart_id == cid)
            cart_qty = int(db.execute(q).scalar_one())
            if max_quantity is not None and agg + cart_qty > max_quantity: break
            constrained.append(cid); agg += cart_qty
        filtered = constrained
    sliced = filtered[offset:] if limit is None else filtered[offset: offset+limit]
    return [{"id": cid, "items": _cart_items_repr(db, cid), "price": _cart_total_price(db, cid)} for cid in sliced]
