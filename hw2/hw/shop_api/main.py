from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect, status, Response
from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
import uuid
import random
import decimal
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)


class ItemInCart(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

class Cart(BaseModel):
    model_config = ConfigDict(json_encoders={decimal.Decimal: lambda v: float(v)})
    id: int
    items: List[ItemInCart] = Field(default_factory=list)
    price: decimal.Decimal = Field(default_factory=lambda: decimal.Decimal('0.00'))

class Item(BaseModel):
    model_config = ConfigDict(json_encoders={decimal.Decimal: lambda v: float(v)})
    id: int
    name: str
    price: decimal.Decimal
    deleted: bool = False

class ItemCreate(BaseModel):
    name: str
    price: decimal.Decimal

class ItemUpdate(BaseModel):
    model_config = ConfigDict(extra='forbid', json_encoders={decimal.Decimal: lambda v: float(v)})
    name: Optional[str] = None
    price: Optional[decimal.Decimal] = None


class Database:
    def __init__(self):
        self.carts: Dict[int, Cart] = {}
        self.items: Dict[int, Item] = {}
        self.next_item_id = 1
        self.next_cart_id = 1

        decimal.getcontext().prec = 10
        self.rounding_context = decimal.Context(prec=10, rounding=decimal.ROUND_HALF_UP)


    def create_item(self, name: str, price: decimal.Decimal) -> Item:
        item_id = self.next_item_id
        self.next_item_id += 1
        item = Item(id=item_id, name=name, price=self.rounding_context.quantize(price, decimal.Decimal('0.01')), deleted=False)
        self.items[item_id] = item
        return item

    def get_item(self, item_id: int) -> Optional[Item]:
        item = self.items.get(item_id)
        if item and item.deleted:
            return None
        return item

    def get_all_items(self, offset: int, limit: int, min_price: Optional[float], max_price: Optional[float], show_deleted: bool) -> List[Item]:
        filtered_items = []
        min_price_dec = decimal.Decimal(str(min_price)) if min_price is not None else None
        max_price_dec = decimal.Decimal(str(max_price)) if max_price is not None else None

        for item in self.items.values():
            if not show_deleted and item.deleted:
                continue
            if min_price_dec is not None and item.price < min_price_dec:
                continue
            if max_price_dec is not None and item.price > max_price_dec:
                continue
            filtered_items.append(item)

        return sorted(filtered_items, key=lambda i: i.id)[offset:offset + limit]

    def update_item(self, item_id: int, item_update: ItemUpdate, partial: bool = False) -> Item:
        item = self.items.get(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        if item.deleted:
            raise HTTPException(status_code=status.HTTP_304_NOT_MODIFIED, detail="Cannot modify a deleted item.")

        if partial: 
            update_data = item_update.model_dump(exclude_unset=True)

            if 'price' in update_data and update_data['price'] is not None:
                update_data['price'] = self.rounding_context.quantize(update_data['price'], decimal.Decimal('0.01'))

            for field, value in update_data.items():
                setattr(item, field, value)
        else: 
            if item_update.name is not None:
                item.name = item_update.name
            if item_update.price is not None:
                item.price = self.rounding_context.quantize(item_update.price, decimal.Decimal('0.01'))

        self._recalculate_cart_prices_for_item(item_id)
        return item

    def delete_item(self, item_id: int):
        item = self.items.get(item_id)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

        if not item.deleted:
            item.deleted = True
            self._recalculate_cart_prices_for_item(item_id)

    def create_cart(self) -> Cart:
        cart_id = self.next_cart_id
        self.next_cart_id += 1
        cart = Cart(id=cart_id, items=[])
        self.carts[cart_id] = cart
        return cart

    def get_cart(self, cart_id: int) -> Optional[Cart]:
        cart = self.carts.get(cart_id)
        if cart:
            self._update_cart_price_and_availability(cart)
        return cart

    def get_all_carts(self, offset: int, limit: int, min_price: Optional[float], max_price: Optional[float], min_quantity: Optional[int], max_quantity: Optional[int]) -> List[Cart]:
        filtered_carts = []
        min_price_dec = decimal.Decimal(str(min_price)) if min_price is not None else None
        max_price_dec = decimal.Decimal(str(max_price)) if max_price is not None else None

        for cart in self.carts.values():
            self._update_cart_price_and_availability(cart)

            if min_price_dec is not None and cart.price < min_price_dec:
                continue
            if max_price_dec is not None and cart.price > max_price_dec:
                continue

            total_quantity = sum(item.quantity for item in cart.items)
            if min_quantity is not None and total_quantity < min_quantity:
                continue
            if max_quantity is not None and total_quantity > max_quantity:
                continue
            filtered_carts.append(cart)

        return sorted(filtered_carts, key=lambda c: c.id)[offset:offset + limit]

    def add_item_to_cart(self, cart_id: int, item_id: int) -> Cart:
        cart = self.carts.get(cart_id)
        if not cart:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")

        item_to_add = self.items.get(item_id)
        if not item_to_add or item_to_add.deleted:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found or deleted")

        found_in_cart = False
        for cart_item in cart.items:
            if cart_item.id == item_id:
                cart_item.quantity += 1
                found_in_cart = True
                break

        if not found_in_cart:
            cart.items.append(ItemInCart(
                id=item_to_add.id,
                name=item_to_add.name,
                quantity=1,
                available=not item_to_add.deleted
            ))

        self._update_cart_price_and_availability(cart)
        return cart

    def _update_cart_price_and_availability(self, cart: Cart):
        total_price = decimal.Decimal('0.00')
        for cart_item in cart.items:
            original_item = self.items.get(cart_item.id)
            if original_item:
                cart_item.name = original_item.name
                cart_item.available = not original_item.deleted
                if not original_item.deleted:
                    total_price += original_item.price * cart_item.quantity
            else:
                cart_item.available = False

        cart.price = self.rounding_context.quantize(total_price, decimal.Decimal('0.01'))

    def _recalculate_cart_prices_for_item(self, item_id: int):
        for cart in self.carts.values():
            for cart_item in cart.items:
                if cart_item.id == item_id:
                    self._update_cart_price_and_availability(cart)
                    break

db = Database()

@app.post("/cart", status_code=status.HTTP_201_CREATED)
async def create_new_cart(response: Response):
    """
    Создает новую корзину и возвращает ее идентификатор.
    """
    cart = db.create_cart()
    response.headers["Location"] = f"/cart/{cart.id}"
    return {"id": cart.id}

@app.get("/cart/{cart_id}", response_model=Cart)
async def get_cart_by_id(cart_id: int):
    """
    Получает корзину по ее идентификатору.
    """
    cart = db.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found")
    return cart

@app.get("/cart", response_model=List[Cart])
async def get_all_carts(
    offset: int = Query(0, ge=0, description="Смещение по списку корзин"),
    limit: int = Query(10, gt=0, description="Ограничение на количество корзин"),
    min_price: Optional[float] = Query(None, ge=0, description="Минимальная общая цена корзины"),
    max_price: Optional[float] = Query(None, ge=0, description="Максимальная общая цена корзины"),
    min_quantity: Optional[int] = Query(None, ge=0, description="Минимальное общее количество товаров в корзине"),
    max_quantity: Optional[int] = Query(None, ge=0, description="Максимальное общее количество товаров в корзине"),
):
    """
    Получает список корзин с возможностью фильтрации и пагинации.
    """
    return db.get_all_carts(offset, limit, min_price, max_price, min_quantity, max_quantity)

@app.post("/cart/{cart_id}/add/{item_id}", response_model=Cart)
async def add_item_to_existing_cart(cart_id: int, item_id: int):
    """
    Добавляет товар в корзину. Если товар уже есть, увеличивает его количество.
    """
    return db.add_item_to_cart(cart_id, item_id)

@app.post("/item", response_model=Item, status_code=status.HTTP_201_CREATED)
async def create_item(item: ItemCreate):
    """
    Добавляет новый товар в магазин.
    """
    new_item = db.create_item(item.name, item.price)
    return new_item

@app.get("/item/{item_id}", response_model=Item)
async def get_item_by_id(item_id: int):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item

@app.get("/item", response_model=List[Item])
async def get_all_items(
    offset: int = Query(0, ge=0, description="Смещение по списку товаров"),
    limit: int = Query(10, gt=0, description="Ограничение на количество товаров"),
    min_price: Optional[float] = Query(None, ge=0, description="Минимальная цена товара"),
    max_price: Optional[float] = Query(None, ge=0, description="Максимальная цена товара"),
    show_deleted: bool = Query(False, description="Показывать ли удаленные товары"),
):
    return db.get_all_items(offset, limit, min_price, max_price, show_deleted)

@app.put("/item/{item_id}", response_model=Item)
async def replace_item(item_id: int, item_update: ItemCreate):
    """
    Полностью заменяет существующий товар по его идентификатору.
    (Нельзя создать новый товар через PUT, только обновить существующий).
    """
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    update_data_for_put = ItemUpdate(name=item_update.name, price=item_update.price)
    return db.update_item(item_id, update_data_for_put, partial=False)


@app.patch("/item/{item_id}", response_model=Item)
async def update_item_partially(item_id: int, item_update: ItemUpdate):
    """
    Частично обновляет товар по его идентификатору.
    Поле 'deleted' нельзя изменить через PATCH.
    """
    return db.update_item(item_id, item_update, partial=True)


@app.delete("/item/{item_id}", status_code=status.HTTP_200_OK)
async def delete_item(item_id: int):
    """
    Помечает товар как удаленный (soft delete).
    Возвращает 200 OK при успешном "удалении" или при повторном запросе на удаление.
    """
    db.delete_item(item_id)
    return Response(status_code=status.HTTP_200_OK)
