from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from http import HTTPStatus
from typing import List, Optional
from sqlalchemy.orm import Session
from Shop_api.database import get_db, Base, engine
from Shop_api.schemas import ItemCreate, Item, Cart
from Shop_api.services.item_service import ItemService
from Shop_api.services.cart_service import CartService
from prometheus_fastapi_instrumentator import Instrumentator
from Shop_api.schemas import CartSchema

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)

#Создание таблиц если не сушествуют
Base.metadata.create_all(bind=engine)

# ------------------ ITEM ENDPOINTS ------------------ #
@app.post("/item", response_model=Item, status_code=HTTPStatus.CREATED)
def create_item(item: ItemCreate, db: Session = Depends(get_db)):
    service = ItemService(db)
    return service.create_item(item)

@app.get("/item/{item_id}", response_model=Item)
def get_item(item_id: int, db: Session = Depends(get_db)):
    service = ItemService(db)
    item = service.get_item(item_id)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item

@app.get("/item", response_model=List[Item])
def list_items(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    db: Session = Depends(get_db)
):
    service = ItemService(db)
    return service.list_items(offset=offset, limit=limit)

@app.put("/item/{item_id}", response_model=Item)
def update_item(item_id: int, new_item: ItemCreate, db: Session = Depends(get_db)):
    service = ItemService(db)
    item = service.update_item(item_id, new_item)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item

@app.delete("/item/{item_id}")
def delete_item(item_id: int, db: Session = Depends(get_db)):
    service = ItemService(db)
    success = service.delete_item(item_id)
    if not success:
        return {"status": "already deleted"}
    return {"status": "deleted"}


# ------------------ CART ENDPOINTS ------------------ #
@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(db: Session = Depends(get_db)):
    service = CartService(db)
    cart = service.create_cart()
    return JSONResponse(
        content={"id": cart.id},
        status_code=HTTPStatus.CREATED,
        headers={"Location": f"/cart/{cart.id}"}
    )

@app.get("/cart/{cart_id}", response_model=Cart)
def get_cart(cart_id: int, db: Session = Depends(get_db)):
    service = CartService(db)
    cart = service.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return cart

@app.post("/cart/{cart_id}/add/{item_id}", response_model=CartSchema)
def add_item_to_cart(cart_id: int, item_id: int, quantity: int = 1, db: Session = Depends(get_db)):
    cart_service = CartService(db)
    updated_cart = cart_service.add_item_to_cart(cart_id, item_id, quantity)


    for cart_item in updated_cart.items:
        if not hasattr(cart_item.item, "deleted") or cart_item.item.deleted is None:
            cart_item.item.deleted = False
        if not hasattr(cart_item.item, "available") or cart_item.item.available is None:
            cart_item.item.available = True

    return updated_cart
