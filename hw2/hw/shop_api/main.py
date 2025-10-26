import os
from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, JSONResponse
from prometheus_client import Counter
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat, BaseModel

from shop_api.models import Cart, Item
from shop_api.models import CartNotFoundException, ItemNotFoundException
from shop_api.in_memory_repository import Repository as InMemoryRepository
from shop_api.postgres_repository import Repository as PostgresRepository


def get_repository(base: str):
    if base == 'in-memory':
        return InMemoryRepository()
    elif base == 'postgres':
        return PostgresRepository()
    raise Exception('Unknown base')


repository = get_repository(os.environ.get('SHOP_API_DB_TYPE', 'in-memory'))

app = FastAPI(title='Shop API')
instrumentator = Instrumentator().instrument(app).expose(app)


@app.post('/cart')
async def create_cart():
    new_cart: Cart = repository.create_cart()
    return JSONResponse(
        content={'id': new_cart.id},
        headers={'location': f'/cart/{new_cart.id}'},
        status_code=status.HTTP_201_CREATED,
    )


test_get_cart_counter = Counter('get_cart_counter', 'Test custum counter')


@app.get('/cart/{id}')
async def get_cart(id: NonNegativeInt):
    test_get_cart_counter.inc()
    try:
        cart = repository.get_cart(id)
    except CartNotFoundException:
        raise HTTPException(status_code=404, detail='Cart not found')
    except Exception as e:
        print("Unexpected internal error: ", e)
        raise HTTPException(status_code=500, detail='Internal server error')
    return cart


@app.get('/cart')
async def get_carts(offset: NonNegativeInt = 0,
                    limit: PositiveInt = 10,
                    min_price: Optional[NonNegativeFloat] = None,
                    max_price: Optional[NonNegativeFloat] = None,
                    min_quantity: Optional[NonNegativeInt] = None,
                    max_quantity: Optional[NonNegativeInt] = None):
    carts: List[Cart] = repository.get_carts(offset, limit)
    result = []
    for cart in carts:
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue

        cart_quantity = sum([item.quantity for item in cart.items])
        if min_quantity is not None and cart_quantity < min_quantity:
            continue
        if max_quantity is not None and cart_quantity > max_quantity:
            continue
        
        result.append(cart)
    
    return result


@app.post('/cart/{cart_id}/add/{item_id}')
async def add_item_to_cart(cart_id: NonNegativeInt, item_id: NonNegativeInt):
    try:
        cart: Cart = repository.add_item_to_cart(cart_id, item_id)
    except CartNotFoundException:
        raise HTTPException(status_code=404, detail='Cart not found')
    except ItemNotFoundException:
        raise HTTPException(status_code=404, detail='Item not found')
    except Exception as e:
        print("Unexpected internal error: ", e)
        raise HTTPException(status_code=500, detail='Internal server errorss')
        

class CreateItemRequestBody(BaseModel):
    name: str
    price: float


@app.post('/item', status_code=201)
async def create_item(body: CreateItemRequestBody):
    new_item: Item = repository.create_item(name=body.name, price=body.price)
    return JSONResponse(
        content=jsonable_encoder(new_item),
        headers={'location': f'/item/{new_item.id}'},
        status_code=status.HTTP_201_CREATED,
    )


@app.get('/item/{id}')
async def get_item(id: NonNegativeInt):
    try:
        item: Item = repository.get_item(id)
    except ItemNotFoundException:
        raise HTTPException(status_code=404, detail='Item not found')
    except Exception as e:
        print("Unexpected internal error: ", e)
        raise HTTPException(status_code=500, detail='Internal server error')
    return item


@app.get('/item')
async def get_items(offset: NonNegativeInt = 0,
                    limit: PositiveInt = 10,
                    min_price: Optional[NonNegativeFloat] = None,
                    max_price: Optional[NonNegativeFloat] = None,
                    show_deleted: bool = False):
    items: List[Item] = repository.get_items(offset, limit)
    result = []
    for item in items:
        if min_price is not None and item.price < min_price:
            continue
        if max_price is not None and item.price > max_price:
            continue
        if not show_deleted and item.deleted:
            continue
        
        result.append(item)
    
    return result


class ReplaceItemRequestBody(BaseModel):
    name: str
    price: float


@app.put('/item/{id}')
async def replace_item(id: NonNegativeInt, body: ReplaceItemRequestBody):
    try:
        item: Item = repository.replace_item(item_id=id, name=body.name, price=body.price)
    except ItemNotFoundException:                                                    
        raise HTTPException(status_code=404, detail='Item not found')
    except Exception as e:
        print("Unexpected internal error: ", e)
        raise HTTPException(status_code=500, detail='Internal server error')
    return item


class UpdateItemRequestBody(BaseModel):
    model_config = {'extra': 'forbid'}

    name: Optional[str] = None
    price: Optional[float] = None


@app.patch('/item/{id}')
async def update_item(id: NonNegativeInt, body: UpdateItemRequestBody):
    try:
        updated_item: Optional[Item] = repository.update_item(
            item_id=id, name=body.name, price=body.price)
    except ItemNotFoundException:
        raise HTTPException(status_code=404, detail='Item not found')
    except Exception as e:
        print("Unexpected internal error: ", e)
        raise HTTPException(status_code=500, detail='Internal server error')
    
    if not updated_item:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    return updated_item


@app.delete('/item/{id}')
async def delete_item(id: NonNegativeInt):
    repository.delete_item(item_id=id)
