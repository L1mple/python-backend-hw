from typing import List, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import Response, JSONResponse
from pydantic import NonNegativeInt, PositiveInt, NonNegativeFloat, BaseModel

from shop_api.models import CartItem, Cart, Item
from shop_api.repository import CartNotFoundException, CartsRepository, ItemNotFoundException, ItemsRepository

app = FastAPI(title="Shop API")


@app.post("/cart")
async def create_cart():
    new_cart: Cart = CartsRepository.create_cart()
    return JSONResponse(
        content={"id": new_cart.id},
        headers={"location": f"/cart/{new_cart.id}"},
        status_code=status.HTTP_201_CREATED,
    )


@app.get("/cart/{id}")
async def get_cart(id: NonNegativeInt):
    try:
        cart = CartsRepository.get_cart(id)
    except CartNotFoundException:
        raise HTTPException(status_code=404, detail="Cart not found")
    return cart


@app.get("/cart")
async def get_carts(offset: NonNegativeInt = 0,
                    limit: PositiveInt = 10,
                    min_price: Optional[NonNegativeFloat] = None,
                    max_price: Optional[NonNegativeFloat] = None,
                    min_quantity: Optional[NonNegativeInt] = None,
                    max_quantity: Optional[NonNegativeInt] = None):
    carts: List[Cart] = CartsRepository.get_carts(offset, limit)
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


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_item_to_cart(cart_id: NonNegativeInt, item_id: NonNegativeInt):
    try:
        cart: Cart = CartsRepository.get_cart(cart_id)
    except CartNotFoundException:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    try:
        item: Item = ItemsRepository.get_item(item_id)
    except ItemNotFoundException:
        raise HTTPException(status_code=404, detail="Item not found")
    
    for cart_item in cart.items:
        if cart_item.id == item.id:
            cart_item.quantity += 1
            break
    else:
        cart.items.append(CartItem(id=item.id, name=item.name, quantity=1,
                                   available=not item.deleted))
    cart.price += item.price

    try:    
        CartsRepository.update_cart(cart)
    except CartNotFoundException:
        raise HTTPException(status_code=500, detail="Internal server error")
        

class CreateItemRequestBody(BaseModel):
    name: str
    price: float


@app.post("/item", status_code=201)
async def create_item(body: CreateItemRequestBody):
    new_item: Item = ItemsRepository.create_item(name=body.name, price=body.price)
    return JSONResponse(
        content=jsonable_encoder(new_item),
        headers={"location": f"/item/{new_item.id}"},
        status_code=status.HTTP_201_CREATED,
    )


@app.get("/item/{id}")
async def get_item(id: NonNegativeInt):
    try:
        item: Item = ItemsRepository.get_item(id)
    except ItemNotFoundException:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.get("/item")
async def get_items(offset: NonNegativeInt = 0,
                    limit: PositiveInt = 10,
                    min_price: Optional[NonNegativeFloat] = None,
                    max_price: Optional[NonNegativeFloat] = None,
                    show_deleted: bool = False):
    items: List[Item] = ItemsRepository.get_items(offset, limit)
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


@app.put("/item/{id}")
async def replace_item(id: NonNegativeInt, body: ReplaceItemRequestBody):
    try:
        item: Item = ItemsRepository.replace_item(item_id=id, name=body.name, price=body.price)
    except ItemNotFoundException:                                                    
        raise HTTPException(status_code=404, detail="Item not found")
    return item


class UpdateItemRequestBody(BaseModel):
    model_config = {"extra": "forbid"}

    name: Optional[str] = None
    price: Optional[float] = None


@app.patch("/item/{id}")
async def update_item(id: NonNegativeInt, body: UpdateItemRequestBody):
    try:
        updated_item: Optional[Item] = ItemsRepository.update_item(
            item_id=id, name=body.name, price=body.price)
    except ItemNotFoundException:
        raise HTTPException(status_code=404, detail="Item not found")
    
    if not updated_item:
        return Response(status_code=status.HTTP_304_NOT_MODIFIED)
    return updated_item


@app.delete("/item/{id}")
async def delete_item(id: NonNegativeInt):
    ItemsRepository.delete_item(item_id=id)
