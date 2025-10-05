import http
from typing import Annotated, List
from fastapi import FastAPI, HTTPException, Query, Response

from shop_api.models import Cart, CartResponse, CreateItemRequest, GeneratedID, GetCartsRequest, GetItemsRequest, Item, UpdateItemRequest
from shop_api.database import  Shop


app = FastAPI(title="Shop API")
shop = Shop()

@app.get("/cart/{cart_id}")
async def get_cart(cart_id: int) -> CartResponse:
    if cart_id not in shop.carts:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return shop.carts[cart_id].create_cart_response(shop.items)[0]


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
    cart_id = shop.current_cart_id
    shop.carts[cart_id] = Cart(id=cart_id, items={})
    shop.current_cart_id += 1
    data = GeneratedID(id=cart_id)
    response.headers["location"] = f"/cart/{cart_id}"
    return data

@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int):
    if cart_id not in shop.carts:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    if item_id not in shop.items or shop.items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    if item_id in shop.carts[cart_id].items:
        shop.carts[cart_id].items[item_id] += 1
    else:
        shop.carts[cart_id].items[item_id] = 0
    return None
    
@app.post("/item", status_code=http.HTTPStatus.CREATED)
async def create_item(payload: CreateItemRequest, response: Response):
    item_id = shop.current_item_id
    item = Item(id=item_id, name = payload.name, price=payload.price, deleted=False)
    shop.current_item_id+=1
    shop.items[item_id] = item
    response.headers["location"] = f"/item/{item_id}"
    return item
    

@app.get("/item/{item_id}")
async def get_item(item_id: int) -> Item:
    if item_id not in shop.items or shop.items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    return shop.items[item_id]


@app.get("/item")
async def get_items(filter: Annotated[GetItemsRequest, Query()]) -> List[Item]:
    filtered_items = []
    
    for item in shop.items.values():
        if filter.min_price is not None and item.price < filter.min_price:
            continue
        if filter.max_price is not None and item.price > filter.max_price:
            continue
        
        if not filter.show_deleted and item.deleted:
            continue
            
        filtered_items.append(item)
    
    left_bound = filter.offset
    right_bound = filter.offset + filter.limit
    return filtered_items[left_bound:right_bound]

@app.put("/item/{item_id}")
async def put_item(item_id: int, payload: CreateItemRequest) -> Item:
    if item_id not in shop.items or shop.items.get(item_id).deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    item = shop.items.get(item_id)
    item.name = payload.name
    item.price = payload.price
    return item

@app.patch("/item/{item_id}")
async def patch_item(item_id: int, payload: UpdateItemRequest) -> Item:
    if item_id not in shop.items:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    if shop.items.get(item_id).deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_MODIFIED)
    item = shop.items.get(item_id)
    if payload.name:
        item.name = payload.name
    if payload.price:
        item.price = payload.price
    return shop.items.get(item_id)


@app.delete("/item/{item_id}")
async def delete_item(item_id: int) -> Item:
    if item_id not in shop.items:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    shop.items[item_id].deleted = True
    return shop.items[item_id]