import http
from typing import Annotated, List
from fastapi import FastAPI, HTTPException, Query, Response

from .models import Cart, CartResponse, CreateItemRequest, GeneratedID, GetCartsRequest, GetItemsRequest, Item, UpdateItemRequest
from .database import  Shop


app = FastAPI(title="Shop API")
shop = Shop()

import http
from typing import Annotated, List
from fastapi import FastAPI, HTTPException, Query, Response
from prometheus_client import Counter, Histogram, Gauge
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator.metrics import (
    latency,
    requests,
    response_size,
    default
)


from .models import Cart, GeneratedID, GetCartsRequest, GetItemsRequest, Item, UpdateItemRequest
from.database import Shop

app = FastAPI(title="Shop API")
shop = Shop()

REQUEST_COUNT = Counter(
    'app_request_count_total', 
    'Total number of HTTP requests', 
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'app_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint']
)

ACTIVE_CARTS = Gauge('app_active_carts', 'Number of active shopping carts')
ITEMS_COUNT = Gauge('app_items_count', 'Total number of items in the shop')
CART_PRICE_SUM = Gauge('app_cart_price_sum', 'Total price of all carts')

def update_business_metrics():
    """Обновляем кастомные бизнес-метрики"""
    ACTIVE_CARTS.set(len(shop.carts))
    ITEMS_COUNT.set(len(shop.items))

instrumentator = Instrumentator()

instrumentator.add(
    default()
).add(
    latency(
        buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
    )
).add(
    requests()
).add(
    response_size()
)

instrumentator.instrument(app).expose(app)

@app.middleware("http")
async def update_metrics_middleware(request, call_next):
    response = await call_next(request)
    update_business_metrics()
    return response


@app.get("/cart/{cart_id}")
async def get_cart(cart_id: int) -> CartResponse:
    cart_response, _ = shop.get_cart_response(cart_id)
    if not cart_response:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return cart_response


@app.get("/cart")
async def get_carts(filter: Annotated[GetCartsRequest, Query()]) -> List[CartResponse]:
    cart_data = [
        cart.create_cart_response(shop.items) for cart in shop.carts.values()
    ]

    def is_fits(cart_tuple) -> bool:
        cart_response, total_quantity = cart_tuple
        price_conditions = [
            filter.min_price is None or filter.min_price <= cart_response.price,
            filter.max_price is None or filter.max_price >= cart_response.price
        ]
        quantity_conditions = [
            filter.min_quantity is None or filter.min_quantity <= total_quantity,
            filter.max_quantity is None or filter.max_quantity >= total_quantity
        ]
        return all(price_conditions + quantity_conditions)
    
    filtered_carts = [
        cart_response for cart_response, total_quantity in cart_data 
        if is_fits((cart_response, total_quantity))
    ]
    left_bound = filter.offset
    right_bound = filter.offset + filter.limit
    return filtered_carts[left_bound:right_bound]

@app.post("/cart", status_code=http.HTTPStatus.CREATED)
async def create_cart(response: Response) -> GeneratedID:
    cart = shop.create_cart()
    #response.headers["location"] = f"/cart/{cart.id}"
    return GeneratedID(id=cart.id)

@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int):
    cart = shop.get_cart(cart_id)
    if cart is None:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    item = shop.get_item(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    updated_cart = shop.add_item_to_cart(cart_id, item_id, quantity=1)
    if updated_cart is None:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return None
    
@app.post("/item", status_code=http.HTTPStatus.CREATED)
async def create_item(payload: CreateItemRequest, response: Response):
    request = CreateItemRequest(name=payload.name, price=payload.price)
    item = shop.create_item(request)
    #response.headers["location"] = f"/item/{item.id}"
    return item
    

@app.get("/item/{item_id}")
async def get_item(item_id: int) -> Item:
    item = shop.get_item(item_id)
    if item is None or item.deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return item


@app.get("/item")
async def get_items(filter: Annotated[GetItemsRequest, Query()]) -> List[Item]:
    request = GetItemsRequest(filter.offset, filter.limit, filter.min_price, filter.max_price, filter.show_deleted)
    filtered_items = shop.get_all_items(request)
    return filtered_items

@app.put("/item/{item_id}")
async def put_item(item_id: int, payload: CreateItemRequest) -> Item:
    updated_item = shop.update_item(item_id, payload)
    if updated_item is None:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return updated_item

@app.patch("/item/{item_id}")
async def patch_item(item_id: int, payload: UpdateItemRequest) -> Item:
    item = shop.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    if item.deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_MODIFIED)
    updated_item = shop.update_item(item_id, payload)
    if updated_item is None:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    
    return updated_item


@app.delete("/item/{item_id}")
async def delete_item(item_id: int) -> Item:
    item = shop.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    success = shop.delete_item(item_id)
    if not success:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return item

