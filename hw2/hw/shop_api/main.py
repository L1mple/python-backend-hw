from http import HTTPStatus
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Response
from pydantic import BaseModel, Field, confloat

app = FastAPI(title="Shop API")

db_items: Dict[int, Dict[str, Any]] = {}
db_carts: Dict[int, Dict[int, int]] = {}
item_id_counter = 0
cart_id_counter = 0



class BaseItem(BaseModel):
    name: str = Field(..., min_length=1)
    price: confloat(gt=0.0)

class Item(BaseItem):
    id: int
    deleted: bool = False
class ItemUpdate(BaseItem):
    pass
class PartialItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    price: Optional[confloat(gt=0.0)] = None
    
    class Config:
        extra = "forbid"


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    items: List[CartItem]
    price: float


class CartCreated(BaseModel):
    id: int


def get_item_or_404(item_id: int, include_deleted: bool = False) -> Dict[str, Any]:
    if item_id not in db_items:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Item with id {item_id} not found")
    item = db_items[item_id]
    if item["deleted"] and not include_deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Item with id {item_id} not found")
    return item


def get_cart_or_404(cart_id: int) -> Dict[int, int]:
    if cart_id not in db_carts:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=f"Cart with id {cart_id} not found")
    return db_carts[cart_id]


def calculate_cart_details(cart_items_dict: Dict[int, int]) -> (List[CartItem], float):
    items_list = []
    total_price = 0.0
    for item_id, quantity in cart_items_dict.items():
        item_db = db_items.get(item_id)
        if item_db:
            is_available = not item_db["deleted"]
            items_list.append(
                CartItem(
                    id=item_id,
                    name=item_db["name"],
                    quantity=quantity,
                    available=is_available,
                )
            )
            if is_available:
                total_price += item_db["price"] * quantity
    return items_list, total_price



@app.post("/item", response_model=Item, status_code=HTTPStatus.CREATED)
def create_item(item: BaseItem):
    global item_id_counter
    item_id_counter += 1
    new_item = {
        "id": item_id_counter,
        "name": item.name,
        "price": item.price,
        "deleted": False,
    }
    db_items[item_id_counter] = new_item
    return new_item


@app.get("/item/{item_id}", response_model=Item)
def get_item(item_id: int):
    return get_item_or_404(item_id)


@app.get("/item", response_model=List[Item])
def get_item_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    show_deleted: bool = False,
):
    filtered_items = []
    for item in db_items.values():
        if not show_deleted and item["deleted"]:
            continue
        if min_price is not None and item["price"] < min_price:
            continue
        if max_price is not None and item["price"] > max_price:
            continue
        filtered_items.append(item)
    return filtered_items[offset : offset + limit]


@app.put("/item/{item_id}", response_model=Item)
def update_item(item_id: int, item_update: ItemUpdate):
    """Полное обновление товара по ID."""
    db_item = get_item_or_404(item_id)

    db_item.update(item_update.dict())
    return db_item


@app.patch("/item/{item_id}", response_model=Item)
def partially_update_item(item_id: int, item_update: PartialItemUpdate, response: Response):
    db_item = get_item_or_404(item_id, include_deleted=True)

    if db_item["deleted"]:
        response.status_code = HTTPStatus.NOT_MODIFIED
        return db_item

    update_data = item_update.dict(exclude_unset=True)
    if not update_data:
        return db_item  # Тест требует 200 OK, если тело пустое

    db_item.update(update_data)
    return db_item


@app.delete("/item/{item_id}", response_model=Item)
def delete_item(item_id: int):
    db_item = get_item_or_404(item_id, include_deleted=True)
    db_item["deleted"] = True
    return db_item



@app.post("/cart", response_model=CartCreated, status_code=HTTPStatus.CREATED)
def create_cart(response: Response):
    global cart_id_counter
    cart_id_counter += 1
    db_carts[cart_id_counter] = {}
    response.headers["Location"] = f"/cart/{cart_id_counter}"
    return {"id": cart_id_counter}


@app.get("/cart/{cart_id}", response_model=Cart)
def get_cart(cart_id: int):
    cart_items_dict = get_cart_or_404(cart_id)
    items_list, total_price = calculate_cart_details(cart_items_dict)
    return Cart(id=cart_id, items=items_list, price=total_price)


@app.get("/cart", response_model=List[Cart])
def get_cart_list(
    offset: int = Query(0, ge=0),
    limit: int = Query(10, gt=0),
    min_price: Optional[float] = Query(None, ge=0.0),
    max_price: Optional[float] = Query(None, ge=0.0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0),
):
    filtered_carts = []
    for cart_id, cart_items_dict in db_carts.items():
        items_list, total_price = calculate_cart_details(cart_items_dict)
        total_quantity = sum(item.quantity for item in items_list)

        if min_price is not None and total_price < min_price:
            continue
        if max_price is not None and total_price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        filtered_carts.append(Cart(id=cart_id, items=items_list, price=total_price))
        
    return filtered_carts[offset : offset + limit]


@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
def add_item_to_cart(cart_id: int, item_id: int):
    cart = get_cart_or_404(cart_id)
    _ = get_item_or_404(item_id)  # Проверяем, что товар существует и не удален

    cart[item_id] = cart.get(item_id, 0) + 1

    items_list, total_price = calculate_cart_details(cart)

    return Cart(id=cart_id, items=items_list, price=total_price)

