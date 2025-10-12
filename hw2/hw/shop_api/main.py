from http import HTTPStatus
from typing import Annotated

from fastapi import FastAPI, HTTPException, Query, Response
from prometheus_fastapi_instrumentator import Instrumentator
from pydantic import BaseModel, Field, field_validator

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)


# ==================== Models ====================


class ItemCreateRequest(BaseModel):
    name: str
    price: float = Field(gt=0)


class ItemPatchRequest(BaseModel):
    name: str | None = None
    price: float | None = Field(default=None, gt=0)

    @field_validator("price", "name")
    @classmethod
    def check_no_deleted(cls, v, info):
        return v

    model_config = {"extra": "forbid"}


class Item(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool = False


class CartItem(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool


class Cart(BaseModel):
    id: int
    items: list[CartItem]
    price: float


class CartResponse(BaseModel):
    id: int


# ==================== Storage ====================


class Storage:
    def __init__(self):
        self.items: dict[int, Item] = {}
        self.carts: dict[int, dict[int, int]] = {}  # cart_id -> {item_id: quantity}
        self.item_counter = 0
        self.cart_counter = 0

    def create_item(self, name: str, price: float) -> Item:
        self.item_counter += 1
        item = Item(id=self.item_counter, name=name, price=price, deleted=False)
        self.items[item.id] = item
        return item

    def get_item(self, item_id: int) -> Item | None:
        return self.items.get(item_id)

    def get_items(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        show_deleted: bool = False,
    ) -> list[Item]:
        items = list(self.items.values())

        # Apply filters
        if not show_deleted:
            items = [item for item in items if not item.deleted]

        if min_price is not None:
            items = [item for item in items if item.price >= min_price]

        if max_price is not None:
            items = [item for item in items if item.price <= max_price]

        # Apply pagination
        return items[offset : offset + limit]

    def update_item(self, item_id: int, name: str, price: float) -> Item | None:
        if item_id not in self.items:
            return None
        self.items[item_id].name = name
        self.items[item_id].price = price
        return self.items[item_id]

    def patch_item(self, item_id: int, name: str | None, price: float | None) -> Item | None:
        if item_id not in self.items:
            return None

        item = self.items[item_id]

        if item.deleted:
            return None

        if name is not None:
            item.name = name
        if price is not None:
            item.price = price

        return item

    def delete_item(self, item_id: int) -> bool:
        if item_id in self.items:
            self.items[item_id].deleted = True
        return True

    def create_cart(self) -> int:
        self.cart_counter += 1
        self.carts[self.cart_counter] = {}
        return self.cart_counter

    def get_cart(self, cart_id: int) -> Cart | None:
        if cart_id not in self.carts:
            return None

        cart_items_dict = self.carts[cart_id]
        items = []
        total_price = 0.0

        for item_id, quantity in cart_items_dict.items():
            item = self.get_item(item_id)
            if item:
                items.append(
                    CartItem(
                        id=item.id,
                        name=item.name,
                        quantity=quantity,
                        available=not item.deleted,
                    )
                )
                if not item.deleted:
                    total_price += item.price * quantity

        return Cart(id=cart_id, items=items, price=total_price)

    def get_carts(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        min_quantity: int | None = None,
        max_quantity: int | None = None,
    ) -> list[Cart]:
        carts = []

        for cart_id in self.carts:
            cart = self.get_cart(cart_id)
            if cart:
                # Apply filters
                if min_price is not None and cart.price < min_price:
                    continue
                if max_price is not None and cart.price > max_price:
                    continue

                total_quantity = sum(item.quantity for item in cart.items)
                if min_quantity is not None and total_quantity < min_quantity:
                    continue
                if max_quantity is not None and total_quantity > max_quantity:
                    continue

                carts.append(cart)

        # Apply pagination
        return carts[offset : offset + limit]

    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        if cart_id not in self.carts:
            return False
        if item_id not in self.items:
            return False

        if item_id in self.carts[cart_id]:
            self.carts[cart_id][item_id] += 1
        else:
            self.carts[cart_id][item_id] = 1

        return True


storage = Storage()


# ==================== Item Endpoints ====================


@app.post("/item", status_code=HTTPStatus.CREATED)
def create_item(item_request: ItemCreateRequest) -> Item:
    """Создание нового товара"""
    return storage.create_item(name=item_request.name, price=item_request.price)


@app.get("/item/{item_id}")
def get_item(item_id: int) -> Item:
    """Получение товара по id"""
    item = storage.get_item(item_id)
    if not item or item.deleted:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@app.get("/item")
def get_items(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    show_deleted: bool = False,
) -> list[Item]:
    """Получение списка товаров с фильтрами"""
    return storage.get_items(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        show_deleted=show_deleted,
    )


@app.put("/item/{item_id}")
def update_item(item_id: int, item_request: ItemCreateRequest) -> Item:
    """Замена товара по id (только существующих)"""
    item = storage.update_item(item_id, name=item_request.name, price=item_request.price)
    if not item:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Item not found")
    return item


@app.patch("/item/{item_id}")
def patch_item(item_id: int, patch_request: ItemPatchRequest) -> Item:
    """Частичное обновление товара по id"""
    item = storage.patch_item(item_id, name=patch_request.name, price=patch_request.price)
    if not item:
        raise HTTPException(
            status_code=HTTPStatus.NOT_MODIFIED, detail="Cannot modify deleted item"
        )
    return item


@app.delete("/item/{item_id}")
def delete_item(item_id: int) -> dict:
    """Удаление товара (пометка как deleted)"""
    storage.delete_item(item_id)
    return {"message": "Item deleted"}


# ==================== Cart Endpoints ====================


@app.post("/cart", status_code=HTTPStatus.CREATED)
def create_cart(response: Response) -> CartResponse:
    """Создание новой корзины"""
    cart_id = storage.create_cart()
    response.headers["location"] = f"/cart/{cart_id}"
    return CartResponse(id=cart_id)


@app.get("/cart/{cart_id}")
def get_cart(cart_id: int) -> Cart:
    """Получение корзины по id"""
    cart = storage.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")
    return cart


@app.get("/cart")
def get_carts(
    offset: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(gt=0)] = 10,
    min_price: Annotated[float | None, Query(ge=0)] = None,
    max_price: Annotated[float | None, Query(ge=0)] = None,
    min_quantity: Annotated[int | None, Query(ge=0)] = None,
    max_quantity: Annotated[int | None, Query(ge=0)] = None,
) -> list[Cart]:
    """Получение списка корзин с фильтрами"""
    return storage.get_carts(
        offset=offset,
        limit=limit,
        min_price=min_price,
        max_price=max_price,
        min_quantity=min_quantity,
        max_quantity=max_quantity,
    )


@app.post("/cart/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int) -> Cart:
    """Добавление товара в корзину"""
    success = storage.add_item_to_cart(cart_id, item_id)
    if not success:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Cart or item not found"
        )

    cart = storage.get_cart(cart_id)
    if not cart:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="Cart not found")

    return cart