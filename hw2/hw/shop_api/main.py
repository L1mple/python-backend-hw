from __future__ import annotations
from http import HTTPStatus

from typing import Annotated, Iterable, List
from dataclasses import dataclass

from fastapi import FastAPI, APIRouter, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, NonNegativeInt, PositiveInt, NonNegativeFloat

from fastapi import WebSocket, WebSocketDisconnect
from uuid import uuid4

# id generator
def _int_id_generator() -> Iterable[int]:
    i = 0
    while True:
        yield i
        i += 1


id_generator = _int_id_generator()


# item models
@dataclass(slots=True)
class ItemInfo:
    name: str
    price: float
    deleted: bool = False


@dataclass(slots=True)
class ItemEntity:
    id: int
    info: ItemInfo


@dataclass(slots=True)
class PatchItemInfo:
    name: str | None = None
    price: float | None = None


# item store
_items_data: dict[int, ItemInfo] = {}


def item_add(info: ItemInfo) -> ItemEntity:
    _id = next(id_generator)
    _items_data[_id] = info
    return ItemEntity(_id, info)


def item_delete(id: int) -> None:
    if id in _items_data:
        _items_data[id].deleted = True


def item_get_one(id: int) -> ItemEntity | None:
    info = _items_data.get(id)
    if info is None or info.deleted:
        return None
    return ItemEntity(id=id, info=info)


def item_get_many(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    show_deleted: bool = False,
) -> Iterable[ItemEntity]:
    curr = 0
    for _id, info in _items_data.items():
        if (not show_deleted) and info.deleted:
            continue
        if min_price is not None and info.price < min_price:
            continue
        if max_price is not None and info.price > max_price:
            continue
        if offset <= curr < offset + limit:
            yield ItemEntity(_id, info)
        curr += 1


def item_update(id: int, info: ItemInfo) -> ItemEntity | None:
    if id not in _items_data or _items_data[id].deleted:
        return None
    _items_data[id] = info
    return ItemEntity(id=id, info=info)


def item_upsert(id: int, info: ItemInfo) -> ItemEntity:
    _items_data[id] = info
    return ItemEntity(id=id, info=info)


def item_patch(id: int, patch_info: PatchItemInfo) -> ItemEntity | None:
    if id not in _items_data or _items_data[id].deleted:
        return None
    if patch_info.name is not None:
        _items_data[id].name = patch_info.name
    if patch_info.price is not None:
        _items_data[id].price = patch_info.price
    return ItemEntity(id=id, info=_items_data[id])


# cart models
@dataclass(slots=True)
class CartItemInfo:
    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class CartInfo:
    items: List[CartItemInfo]
    price: float


@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo


@dataclass(slots=True)
class PatchCartInfo:
    items: List[CartItemInfo] | None = None
    price: float | None = None


# cart store
_carts_data: dict[int, CartInfo] = {}


def cart_add_empty() -> CartEntity:
    _id = next(id_generator)
    _carts_data[_id] = CartInfo(items=[], price=0.0)
    return CartEntity(_id, _carts_data[_id])


def _cart_recalculate(info: CartInfo) -> CartInfo:
    total_price = 0.0
    new_items: list[CartItemInfo] = []
    for it in info.items:
        entity = item_get_one(it.id)
        available = entity is not None
        name = entity.info.name if entity is not None else it.name
        price = entity.info.price if entity is not None else 0.0
        if available:
            total_price += price * it.quantity
        new_items.append(CartItemInfo(id=it.id, name=name, quantity=it.quantity, available=available))
    return CartInfo(items=new_items, price=total_price)


def cart_get_one(id: int) -> CartEntity | None:
    if id not in _carts_data:
        return None
    recalculated = _cart_recalculate(_carts_data[id])
    return CartEntity(id=id, info=recalculated)


def cart_get_many(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None,
) -> Iterable[CartEntity]:
    curr = 0
    for _id, info in _carts_data.items():
        recalculated = _cart_recalculate(info)
        total_quantity = sum(i.quantity for i in recalculated.items)
        if min_price is not None and recalculated.price < min_price:
            continue
        if max_price is not None and recalculated.price > max_price:
            continue
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
        if offset <= curr < offset + limit:
            yield CartEntity(_id, recalculated)
        curr += 1


def cart_update(id: int, info: CartInfo) -> CartEntity | None:
    if id not in _carts_data:
        return None
    _carts_data[id] = info
    return CartEntity(id=id, info=info)


def cart_upsert(id: int, info: CartInfo) -> CartEntity:
    _carts_data[id] = info
    return CartEntity(id=id, info=info)


def cart_patch(id: int, patch_info: PatchCartInfo) -> CartEntity | None:
    if id not in _carts_data:
        return None
    if patch_info.items is not None:
        _carts_data[id].items = patch_info.items
    recalculated = _cart_recalculate(_carts_data[id])
    _carts_data[id] = recalculated
    return CartEntity(id=id, info=recalculated)


def cart_add_item(cart_id: int, item_id: int) -> CartEntity | None:
    if cart_id not in _carts_data:
        return None
    existing = _carts_data[cart_id]
    item_entity = item_get_one(item_id)
    name = item_entity.info.name if item_entity is not None else f"item-{item_id}"
    for it in existing.items:
        if it.id == item_id:
            it.quantity += 1
            break
    else:
        existing.items.append(
            CartItemInfo(id=item_id, name=name, quantity=1, available=item_entity is not None)
        )
    recalculated = _cart_recalculate(existing)
    _carts_data[cart_id] = recalculated
    return CartEntity(id=cart_id, info=recalculated)


# item contracts
class ItemResponse(BaseModel):
    id: int
    name: str
    price: float
    deleted: bool

    @staticmethod
    def from_entity(entity: ItemEntity) -> ItemResponse:
        return ItemResponse(
            id=entity.id,
            name=entity.info.name,
            price=entity.info.price,
            deleted=entity.info.deleted,
        )


class ItemRequest(BaseModel):
    name: str
    price: float
    deleted: bool = False

    def as_item_info(self) -> ItemInfo:
        return ItemInfo(name=self.name, price=self.price, deleted=self.deleted)


class PatchItemRequest(BaseModel):
    name: str | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_item_info(self) -> PatchItemInfo:
        return PatchItemInfo(name=self.name, price=self.price)


# cart contracts
class CartItemResponse(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    @staticmethod
    def from_cart_item_info(cart_item: CartItemInfo) -> CartItemResponse:
        return CartItemResponse(
            id=cart_item.id,
            name=cart_item.name,
            quantity=cart_item.quantity,
            available=cart_item.available,
        )


class CartResponse(BaseModel):
    id: int
    items: List[CartItemResponse]
    price: float

    @staticmethod
    def from_entity(entity: CartEntity) -> CartResponse:
        return CartResponse(
            id=entity.id,
            items=[CartItemResponse.from_cart_item_info(item) for item in entity.info.items],
            price=entity.info.price,
        )


class CartItemRequest(BaseModel):
    id: int
    name: str
    quantity: int
    available: bool

    def as_cart_item_info(self) -> CartItemInfo:
        return CartItemInfo(
            id=self.id,
            name=self.name,
            quantity=self.quantity,
            available=self.available,
        )


class CartRequest(BaseModel):
    items: List[CartItemRequest]
    price: float

    def as_cart_info(self) -> CartInfo:
        return CartInfo(
            items=[item.as_cart_item_info() for item in self.items],
            price=self.price,
        )


class PatchCartItemRequest(BaseModel):
    id: int | None = None
    name: str | None = None
    quantity: int | None = None
    available: bool | None = None

    model_config = ConfigDict(extra="forbid")


class PatchCartRequest(BaseModel):
    items: List[CartItemRequest] | None = None
    price: float | None = None

    model_config = ConfigDict(extra="forbid")

    def as_patch_cart_info(self) -> PatchCartInfo:
        return PatchCartInfo(
            items=[item.as_cart_item_info() for item in self.items] if self.items else None,
            price=self.price,
        )

# char room manager
class ChatRoomManager:
    def __init__(self) -> None:
        self.rooms: dict[str, set[WebSocket]] = {}

    async def connect(self, chat_name: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.rooms.setdefault(chat_name, set()).add(websocket)

    def disconnect(self, chat_name: str, websocket: WebSocket) -> None:
        room = self.rooms.get(chat_name)
        if not room:
            return
        if websocket in room:
            room.remove(websocket)
        if not room:
            self.rooms.pop(chat_name, None)

    async def broadcast(self, chat_name: str, message: str, exclude: WebSocket | None = None) -> None:
        room = self.rooms.get(chat_name)
        if not room:
            return
        for ws in list(room):
            if exclude is not None and ws is exclude:
                continue
            try:
                await ws.send_text(message)
            except Exception:
                if ws in room:
                    room.remove(ws)

chat_manager = ChatRoomManager()

# generate username
def generate_username() -> str:
    return f"user-{uuid4().hex[:8]}"

# item router
item_router = APIRouter(prefix="/item")


@item_router.get("/")
async def get_item_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    show_deleted: Annotated[bool, Query()] = False,
) -> list[ItemResponse]:
    return [
        ItemResponse.from_entity(e)
        for e in item_get_many(
            offset=offset,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            show_deleted=show_deleted,
        )
    ]


@item_router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Successfully returned requested item"},
        HTTPStatus.NOT_FOUND: {"description": "Failed to return requested item as one was not found"},
    },
)
async def get_item_by_id(id: int) -> ItemResponse:
    entity = item_get_one(id)
    if not entity:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Request resource /item/{id} was not found")
    return ItemResponse.from_entity(entity)


@item_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_item(info: ItemRequest, response: Response) -> ItemResponse:
    entity = item_add(info.as_item_info())
    response.headers["location"] = f"/item/{entity.id}"
    return ItemResponse.from_entity(entity)


@item_router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Successfully patched item"},
        HTTPStatus.NOT_MODIFIED: {"description": "Failed to modify item as one was not found"},
    },
)
async def patch_item(id: int, info: PatchItemRequest) -> ItemResponse:
    entity = item_patch(id, info.as_patch_item_info())
    if entity is None:
        raise HTTPException(HTTPStatus.NOT_MODIFIED, f"Requested resource /item/{id} was not found")
    return ItemResponse.from_entity(entity)


@item_router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Successfully updated or upserted item"},
        HTTPStatus.NOT_MODIFIED: {"description": "Failed to modify item as one was not found"},
    },
)
async def put_item(
    id: int,
    info: ItemRequest,
    upsert: Annotated[bool, Query()] = False,
) -> ItemResponse:
    entity = item_upsert(id, info.as_item_info()) if upsert else item_update(id, info.as_item_info())
    if entity is None:
        raise HTTPException(HTTPStatus.NOT_MODIFIED, f"Requested resource /item/{id} was not found")
    return ItemResponse.from_entity(entity)


@item_router.delete("/{id}")
async def delete_item(id: int) -> Response:
    item_delete(id)
    return Response("")


# cart router
cart_router = APIRouter(prefix="/cart")


@cart_router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat | None, Query()] = None,
    max_price: Annotated[NonNegativeFloat | None, Query()] = None,
    min_quantity: Annotated[NonNegativeInt | None, Query()] = None,
    max_quantity: Annotated[NonNegativeInt | None, Query()] = None,
) -> list[CartResponse]:
    return [
        CartResponse.from_entity(e)
        for e in cart_get_many(
            offset=offset,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
        )
    ]


@cart_router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Successfully returned requested cart"},
        HTTPStatus.NOT_FOUND: {"description": "Failed to return requested cart as one was not found"},
    },
)
async def get_cart_by_id(id: int) -> CartResponse:
    entity = cart_get_one(id)
    if not entity:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Request resource /cart/{id} was not found")
    return CartResponse.from_entity(entity)


@cart_router.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
async def post_cart(response: Response) -> dict[str, int]:
    entity = cart_add_empty()
    response.headers["location"] = f"/cart/{entity.id}"
    return {"id": entity.id}


@cart_router.patch(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Successfully patched cart"},
        HTTPStatus.NOT_MODIFIED: {"description": "Failed to modify cart as one was not found"},
    },
)
async def patch_cart(id: int, info: PatchCartRequest) -> CartResponse:
    entity = cart_patch(id, info.as_patch_cart_info())
    if entity is None:
        raise HTTPException(HTTPStatus.NOT_MODIFIED, f"Requested resource /cart/{id} was not found")
    return CartResponse.from_entity(entity)


@cart_router.put(
    "/{id}",
    responses={
        HTTPStatus.OK: {"description": "Successfully updated or upserted cart"},
        HTTPStatus.NOT_MODIFIED: {"description": "Failed to modify cart as one was not found"},
    },
)
async def put_cart(
    id: int,
    info: CartRequest,
    upsert: Annotated[bool, Query()] = False,
) -> CartResponse:
    entity = cart_upsert(id, info.as_cart_info()) if upsert else cart_update(id, info.as_cart_info())
    if entity is None:
        raise HTTPException(HTTPStatus.NOT_MODIFIED, f"Requested resource /cart/{id} was not found")
    return CartResponse.from_entity(entity)


@cart_router.post("/{cart_id}/add/{item_id}")
async def add_item(cart_id: int, item_id: int) -> Response:
    entity = cart_add_item(cart_id, item_id)
    if entity is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"/cart/{cart_id} not found")
    return Response("")


# app
app = FastAPI(title="Shop API")
app.include_router(cart_router)
app.include_router(item_router)


# websocket chat
@app.websocket("/chat/{chat_name}")
async def websocket_chat(websocket: WebSocket, chat_name: str) -> None:
    username = generate_username()
    await chat_manager.connect(chat_name, websocket)
    try:
        while True:
            text = await websocket.receive_text()
            await chat_manager.broadcast(chat_name, f"{username} :: {text}", exclude=websocket)
    except WebSocketDisconnect:
        chat_manager.disconnect(chat_name, websocket)