from http import HTTPStatus
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query, Response
from pydantic import NonNegativeInt, PositiveInt

from hw2.hw.shop_api import store
from hw2.hw.shop_api.contracts import (
    CartResponse,
    ItemRequest,
    ItemResponse,
    PatchItemRequest,
    PutItemRequest,
)
from hw2.hw.shop_api.models import ItemEntity

cartRouter = APIRouter(prefix="/cart")
itemRouter = APIRouter(prefix="/item")

databaseStore = store.DatabaseStore()

@cartRouter.post("/", status_code=HTTPStatus.CREATED)
async def create_cart(response: Response):
    id = databaseStore.create_cart()
    
    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/cart/{id}"
    
    return { "id": id }


@cartRouter.get(
    "/{id}",
     responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested pokemon",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested pokemon as one was not found",
        },
    },
)
async def get_cart(id: int) -> CartResponse:
    cart = databaseStore.get_cart(id)
    if cart is None:
        raise HTTPException(status_code=404, detail="Cart not found")
    return CartResponse.from_entity(cart)


@cartRouter.get("/")
async def get_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    min_quantity: Optional[int] = Query(None, ge=0),
    max_quantity: Optional[int] = Query(None, ge=0)
) -> list[CartResponse]:
    carts = databaseStore.get_all_carts()
    
    if min_price is not None:
        carts = [cart for cart in carts if cart.info.price >= min_price]
    
    if max_price is not None:
        carts = [cart for cart in carts if cart.info.price <= max_price]
    
    if min_quantity is not None:
        carts = [cart for cart in carts if cart.info.price >= min_quantity]
    
    if max_quantity is not None:
        carts = [cart for cart in carts if cart.info.price <= max_quantity]
    
    return [CartResponse.from_entity(entity) for entity in carts[offset:offset + limit]]


@cartRouter.post("/{cart_id}/add/{item_id}")
def add_item_to_cart(cart_id: int, item_id: int):
    item = databaseStore.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    
    success = databaseStore.add_item_to_cart(cart_id, item)
    if not success:
        raise HTTPException(status_code=404, detail="Cart not found")
    
    return {"message": "Item added to cart"}


@itemRouter.post(
    "/",
    status_code=HTTPStatus.CREATED,
)
def post_item(info: ItemRequest, response: Response) -> ItemResponse:
    entity = databaseStore.add_item(info.as_item_info())

    # as REST states one should provide uri to newly created resource in location header
    response.headers["location"] = f"/item/{entity.id}"

    return ItemResponse.from_entity(entity)


@itemRouter.get(
    "/{item_id}",
     responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested pokemon",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested pokemon as one was not found",
        },
    },
)
async def get_item(item_id: int) -> ItemResponse:
    item = databaseStore.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse.from_entity(item)


@itemRouter.get("/")
async def get_items(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None, ge=0),
    show_deleted: Optional[bool] = Query(False),
) -> list[ItemResponse]:
    items = databaseStore.get_all_items()
    
    if not show_deleted:
        items = [item for item in items if not item.info.deleted]
    

    if min_price is not None:
        items = [item for item in items if item.info.price >= min_price]
    
    if max_price is not None:
        items = [item for item in items if item.info.price <= max_price]

    return [ItemResponse.from_entity(entity) for entity in items[offset:offset + limit]]


@itemRouter.put("/{item_id}")
def update_item(item_id: int, request: PutItemRequest) -> ItemResponse:
    item = databaseStore.put_item(item_id=item_id, request=request)
    if item is None:
         raise HTTPException(status_code=404, detail="Item not found")
    return ItemResponse.from_entity(item)


@itemRouter.patch(
    "/{item_id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully patched item",
        },
        HTTPStatus.NOT_MODIFIED: {
            "description": "Failed to modify item as one was not found",
        },
        HTTPStatus.UNPROCESSABLE_ENTITY: {
            "description": "invalid price",
        },
    }
)
async def patch_item(item_id: int, info: PatchItemRequest):
    entity = databaseStore.patch_item(item_id, info.as_patch_item_info())
    
    if isinstance(entity, ItemEntity):
        return ItemResponse.from_entity(entity)
    else:
        match entity:
            case databaseStore.PatchResult.NotFound:
                raise HTTPException(status_code=404, detail="Item not found")
            case databaseStore.PatchResult.NotModified:
                return Response(status_code=304)
            case _:
                raise HTTPException(status_code=422, detail="Incorrect price")


@itemRouter.delete("/{item_id}")
async def delete_item(item_id: int):
    databaseStore.delete_item(item_id)
    return {"message": "Item deleted"}