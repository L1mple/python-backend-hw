from typing import List
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Path, Depends, HTTPException, Response
from prometheus_fastapi_instrumentator import Instrumentator

from shop_api.db_manager import DB
from shop_api.models import (
    Item,
    Cart,
    ItemRequest,
    ItemPatchRequest,
    ItemFilterParams,
    CartCreateResponse,
    CartFilterParams,
    NotFoundError,
    NotModifiedError
)

@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = DB()
    yield
    app.state.db.close()

app = FastAPI(title="Shop API", lifespan=lifespan)
Instrumentator().instrument(app).expose(app)


def get_db(request: Request) -> DB:
    db: DB = request.app.state.db
    return db


@app.post(
    "/item",
    response_model=Item,
    status_code=201
)
def create_item(
    item: ItemRequest,
    db: DB = Depends(get_db)
):
    new_item = db.create_item(item.name, item.price)
    return new_item

@app.get(
    "/item/{id}",
    response_model=Item,
    status_code=200
)
def get_item(
    id: int = Path(..., description="ID товара"),
    db: DB = Depends(get_db)
):
    item = db.get_item_by_id(id)
    if not item:
        raise HTTPException(404, detail="Товар не найден")
    return item

@app.get(
    "/item",
    response_model=List[Item],
    status_code=200
)
def get_items(
    items_params: ItemFilterParams = Depends(),
    db: DB = Depends(get_db)
):
    item_list = db.get_items(items_params)
    return item_list

@app.put(
    "/item/{id}",
    response_model=Item,
    status_code=200
)
def replace_item(
    item: ItemRequest,
    id: int = Path(..., description="ID товара"),
    db: DB = Depends(get_db)
):
    try:
        new_item = db.replace_item(id, item.name, item.price)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))
    return new_item

@app.patch(
    "/item/{id}",
    response_model=Item,
    status_code=200
)
def edit_item(
    patch_data: ItemPatchRequest,
    id: int = Path(..., description="ID товара"),
    db: DB = Depends(get_db)
):
    try:
        updated_item = db.edit_item(id, patch_data.name, patch_data.price)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))
    except NotModifiedError as e:
        return Response(status_code=304)
    return updated_item

@app.delete(
    "/item/{id}",
    status_code=200
)
def delete_item(id: int = Path(..., description="ID товара"), db: DB = Depends(get_db)):
    try:
        res = db.delete_item(id)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))
    return res

@app.post(
    "/cart",
    response_model=CartCreateResponse,
    status_code=201
)
def create_cart(response: Response, db: DB = Depends(get_db)):
    cart = db.create_cart()
    response.headers["Location"] = f"/cart/{cart.id}"
    return cart

@app.get(
    "/cart/{id}",
    response_model=Cart,
    status_code=200
)
def get_cart(
    id: int = Path(..., description="ID коризны"),
    db: DB = Depends(get_db)
):
    cart = db.get_cart_by_id(id)
    if not cart:
        raise HTTPException(404, detail="Корзина не найдена")
    return cart

@app.get(
    "/cart",
    response_model=List[Cart],
    status_code=200
)
def get_carts(
    cart_params: CartFilterParams = Depends(),
    db: DB = Depends(get_db)
):
    cart_list = db.get_carts(cart_params)
    return cart_list

@app.post(
    "/cart/{cart_id}/add/{item_id}",
    status_code=204
)
def add_item_to_cart(
    cart_id: int = Path(..., description="ID корзины"),
    item_id: int = Path(..., description="ID товара"),
    db: DB = Depends(get_db)
):
    try:
        res = db.add_item_to_cart(cart_id, item_id)
    except NotFoundError as e:
        raise HTTPException(404, detail=str(e))
    return res

if __name__ == '__main__':
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
