from fastapi import FastAPI, Depends, HTTPException, Query, Response
from http import HTTPStatus
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from store import models, queries, schemas
from store.database import engine, SessionLocal

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Shop API with DB")
Instrumentator().instrument(app).expose(app)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/item", response_model=schemas.Item, status_code=HTTPStatus.CREATED)
def create_item(item: schemas.ItemCreate, db: Session = Depends(get_db)):
    return queries.create_item(db, item.name, item.price)


@app.get("/item/{item_id}", response_model=schemas.Item)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = queries.get_item(db, item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@app.get("/item", response_model=list[schemas.Item])
def list_items(db: Session = Depends(get_db)):
    return queries.list_items(db)


@app.put("/item/{item_id}", response_model=schemas.Item)
def replace_item(item_id: int, item: schemas.ItemBase, db: Session = Depends(get_db)):
    updated = queries.update_item(db, item_id, item.name, item.price)
    if not updated:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return updated


@app.patch("/item/{item_id}", response_model=schemas.Item)
def patch_item(item_id: int, data: dict, db: Session = Depends(get_db)):
    updated = queries.patch_item(db, item_id, data)
    if not updated:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return updated


@app.delete("/item/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    deleted = queries.delete_item(db, item_id)
    return {"status": "deleted" if deleted else "not found"}


@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(db: Session = Depends(get_db)):
    cart = queries.create_cart(db)
    return {"id": cart.id}


@app.get("/cart/{cart_id}", response_model=schemas.Cart)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    cart = queries.get_cart(db, cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return cart


@app.get("/cart", response_model=list[schemas.Cart])
def list_carts(db: Session = Depends(get_db)):
    return queries.list_carts(db)


@app.post("/cart/{cart_id}/add/{item_id}", response_model=schemas.Cart)
def add_to_cart(cart_id: int, item_id: int, db: Session = Depends(get_db)):
    cart = queries.add_to_cart(db, cart_id, item_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND)
    return cart
