import http
import itertools
import typing

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Response, Query
from prometheus_fastapi_instrumentator import Instrumentator
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import insert, select, update

import shop_api.tables as tables
import shop_api.schemas as schemas


@asynccontextmanager
async def setup_db(app: FastAPI):
    async with tables.engine.begin() as conn:
        await conn.run_sync(tables.Base.metadata.drop_all)
        await conn.run_sync(tables.Base.metadata.create_all)
    yield


app = FastAPI(lifespan=setup_db, title="Shop API")
app = FastAPI(title="Shop API")

Instrumentator(
    excluded_handlers=["/metrics"],
).instrument(app).expose(app)


async def get_session():
    async with tables.AsyncSessionLocal() as session:
        yield session


Session = typing.Annotated[AsyncSession, Depends(get_session)]


class Store:
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_item(self, name: str, price: float) -> schemas.Item:
        stmt = insert(tables.Item).values(name=name, price=price).returning(tables.Item)
        created_item = (await self.session.execute(stmt)).scalar_one()
        return schemas.Item.model_validate(created_item, from_attributes=True)
    
    async def update_item(self, item: schemas.Item) -> schemas.Item:
        stmt = update(
            tables.Item
        ).where(
            tables.Item.id == item.id
        ).values(
            name=item.name, price=item.price, deleted=item.deleted
        ).returning(
            tables.Item
        )
        updated_item = (await self.session.execute(stmt)).scalar_one()
        return schemas.Item.model_validate(updated_item, from_attributes=True)
    
    async def get_items(
            self,
            item_id: int | None = None,
            item_ids: list[int] | None = None,
        ) -> dict[int, schemas.Item]:
        stmt = select(tables.Item)
        if item_id:
            stmt = stmt.where(tables.Item.id == item_id)
        if item_ids:
            stmt = stmt.where(tables.Item.id.in_(item_ids))
        items = (await self.session.execute(stmt)).scalars().all()
        return {
            item.id: schemas.Item.model_validate(item, from_attributes=True)
            for item in items
        }
    
    async def create_cart(self) -> schemas.Cart:
        stmt = insert(tables.Cart).values(items={}).returning(tables.Cart)
        created_cart = (await self.session.execute(stmt)).scalar_one()
        return schemas.Cart.model_validate(created_cart, from_attributes=True)
    
    async def update_cart(self, cart: schemas.Cart) -> schemas.Cart:
        stmt = update(
            tables.Cart
        ).where(
            tables.Cart.id == cart.id
        ).values(
            items=cart.items,
        ).returning(
            tables.Cart
        )
        updated_cart = (await self.session.execute(stmt)).scalar_one()
        return schemas.Cart.model_validate(updated_cart, from_attributes=True)
    
    async def get_carts(self, cart_id: int | None = None) -> dict[int, schemas.Cart]:
        stmt = select(tables.Cart)
        if cart_id:
            stmt = stmt.where(tables.Cart.id == cart_id)
        carts = (await self.session.execute(stmt)).scalars().all()
        return {
            cart.id: schemas.Cart.model_validate(cart, from_attributes=True)
            for cart in carts
        }


async def get_store(session: Session):
    store = Store(session)
    yield store
    await session.commit()


Store = typing.Annotated[Store, Depends(get_store)]


@app.post("/cart", status_code=http.HTTPStatus.CREATED)
async def create_cart(response: Response, store: Store) -> schemas.WrappedID:
    created_cart = await store.create_cart()
    data = schemas.WrappedID(id=created_cart.id)
    response.headers["location"] = f"/cart/{created_cart.id}"
    return data


@app.get("/cart/{cart_id}")
async def get_cart(cart_id: int, store: Store) -> schemas.CartResponse:
    carts = await store.get_carts(cart_id=cart_id)
    if not carts:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)  # pragma: no cover
    items = await store.get_items(item_ids=list(carts[cart_id].items.keys()))
    return carts[cart_id].create_cart_response(items)[0]


@app.get("/cart")
async def get_carts(
    filter: typing.Annotated[schemas.GetCartsRequest, Query()],
    store: Store,
) -> list[schemas.CartResponse]:
    carts = await store.get_carts()
    items = await store.get_items()
    prepared_carts: typing.Generator[tuple[schemas.CartResponse, int]] = (
        cart.create_cart_response(items) for cart in carts.values()
    )
    filtered_carts = (
        cart
        for cart, quantity in prepared_carts
        if all(
            (
                (filter.min_price is None or cart.price >= filter.min_price),
                (filter.max_price is None or cart.price <= filter.max_price),
                (filter.min_quantity is None or quantity >= filter.min_quantity),
                (filter.max_quantity is None or quantity <= filter.max_quantity),
            )
        )
    )
    return list(
        itertools.islice(filtered_carts, filter.offset, filter.offset + filter.limit)
    )


@app.post("/cart/{cart_id}/add/{item_id}")
async def add_to_cart(cart_id: int, item_id: int, store: Store):
    carts = await store.get_carts(cart_id=cart_id)
    if not carts:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)  # pragma: no cover
    items = await store.get_items(item_id=item_id)
    if not items or items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)  # pragma: no cover
    if item_id in carts[cart_id].items:
        carts[cart_id].items[item_id] += 1
    else:
        carts[cart_id].items[item_id] = 1
    await store.update_cart(carts[cart_id])
    return None


@app.post("/item", status_code=http.HTTPStatus.CREATED)
async def create_item(
    payload: schemas.CreateItemRequest,
    response: Response,
    store: Store,
) -> schemas.Item:
    item = await store.create_item(name=payload.name, price=payload.price)
    response.headers["location"] = f"/item/{item.id}"
    return item


@app.get("/item/{item_id}")
async def get_item(item_id: int, store: Store) -> schemas.Item:
    items = await store.get_items(item_id=item_id)
    if not items or items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)  # pragma: no cover
    return items[item_id]


@app.get("/item")
async def get_items(
    filter: typing.Annotated[schemas.GetItemsRequest, Query()],
    store: Store,
) -> list[schemas.Item]:
    items = await store.get_items()
    filtered_items = (
        item
        for item in items.values()
        if all(
            (
                (filter.min_price is None or item.price >= filter.min_price),
                (filter.max_price is None or item.price <= filter.max_price),
                (not item.deleted or filter.show_deleted),
            )
        )
    )
    return list(
        itertools.islice(filtered_items, filter.offset, filter.offset + filter.limit)
    )


@app.put("/item/{item_id}")
async def put_item(
    item_id: int,
    payload: schemas.CreateItemRequest,
    store: Store,
) -> schemas.Item:
    items = await store.get_items(item_id=item_id)
    if not items:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)  # pragma: no cover
    items[item_id].name = payload.name
    items[item_id].price = payload.price
    return await store.update_item(items[item_id])


@app.patch("/item/{item_id}")
async def patch_item(
    item_id: int,
    payload: schemas.UpdateItemRequest,
    store: Store,
) -> schemas.Item:
    items = await store.get_items(item_id=item_id)
    if not items:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)  # pragma: no cover
    if items[item_id].deleted:
        raise HTTPException(status_code=http.HTTPStatus.NOT_MODIFIED)  # pragma: no cover
    if payload.name:
        items[item_id].name = payload.name
    if payload.price:
        items[item_id].price = payload.price
    return await store.update_item(items[item_id])


@app.delete("/item/{item_id}")
async def delete_item(item_id: int, store: Store) -> schemas.Item:
    items = await store.get_items(item_id=item_id)
    if not items:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)  # pragma: no cover
    items[item_id].deleted = True
    return await store.update_item(items[item_id])
