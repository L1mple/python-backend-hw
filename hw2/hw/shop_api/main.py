from dataclasses import dataclass
from http import HTTPStatus
from typing import Any, Optional

from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from prometheus_fastapi_instrumentator import Instrumentator


@dataclass
class Item:
    name: str
    price: float
    deleted: bool = False

    def serialize(self, id: int) -> dict[str, Any]:
        return {
            "id": id,
            "name": self.name,
            "price": self.price,
            "deleted": self.deleted,
        }


items: dict[int, Item] = {}


class Cart:
    def __init__(self, id: int) -> None:
        self.id = id
        self.items: dict[int, int] = {}

    def add_item(self, id: int) -> None:
        if id in self.items:
            self.items[id] += 1
        else:
            self.items[id] = 1

    def quantity(self):
        return sum(
            [0 if items[id].deleted else q for id, q in self.items.items()]
        )

    def price(self):
        sum = 0.0
        for id, q in self.items.items():
            if not items[id].deleted:
                sum += q * items[id].price
        return sum

    def serialize(self) -> dict[str, Any]:
        res: dict[str, Any] = {}
        res["id"] = self.id
        res["price"] = self.price()
        res["items"] = []
        for id in self.items.keys():
            res["items"].append(
                {
                    "id": id,
                    "name": items[id].name,
                    "quantity": self.items[id],
                    "available": not items[id].deleted,
                }
            )
        return res


carts: list[Cart] = []

app = FastAPI(title="Shop API")
Instrumentator().instrument(app).expose(app)


@app.post("/cart")
def create_cart():
    id = len(carts)
    carts.append(Cart(id))
    return JSONResponse(
        status_code=HTTPStatus.CREATED,
        content={"id": id},
        headers={"Location": f"/cart/{id}"},
    )


@app.get("/cart/{id}")
def get_cart_by_id(id: int):
    for cart in carts:
        if cart.id == id:
            return cart.serialize()

    return JSONResponse(
        status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        content={"message": "no such id"},
    )


@app.get("/cart")
def get_cart_with_params(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    min_quantity: Optional[int] = Query(default=None, ge=0),
    max_quantity: Optional[int] = Query(default=None, ge=0),
):
    return list(
        map(
            lambda x: x.serialize(),
            filter(
                lambda x: (min_price is None or x.price() >= min_price)
                and (max_price is None or x.price() <= max_price)
                and (min_quantity is None or x.quantity() >= min_quantity)
                and (max_quantity is None or x.quantity() <= max_quantity),
                carts[offset : offset + limit],
            ),
        )
    )


@app.post("/cart/{cart_id}/add/{item_id}")
def post_cart(cart_id: int, item_id: int):
    if cart_id >= len(carts):
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            content={"message": "no such cart_id"},
        )
    carts[cart_id].add_item(item_id)


@app.post("/item")
def add_item(item: Item):
    id = len(items)
    items[id] = item
    return JSONResponse(
        status_code=HTTPStatus.CREATED, content=items[id].serialize(id)
    )


@app.get("/item/{id}")
def get_item_by_id(id: int):
    if id in items and not items[id].deleted:
        return items[id].serialize(id)
    return JSONResponse(
        status_code=HTTPStatus.NOT_FOUND, content={"message": "not found"}
    )


@app.get("/item")
def get_item_query(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=10, ge=1),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    show_deleted=False,
):
    return [
        x.serialize(id)
        for id, x in list(items.items())[offset : offset + limit]
        if (min_price is None or x.price >= min_price)
        and (max_price is None or x.price <= max_price)
        and (show_deleted or not x.deleted)
    ]


@app.put("/item/{id}")
def put_item(id: int, item: Item):
    items[id] = item
    return JSONResponse(status_code=HTTPStatus.OK, content=item.serialize(id))


class ItemUpdate(BaseModel):
    name: Optional[str] = None
    price: Optional[float] = None
    model_config = ConfigDict(extra="forbid")


@app.patch("/item/{id}")
def patch_item(id: int, updates: ItemUpdate):
    if id not in items:
        return JSONResponse(
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
            content={"message": "not found"},
        )
    if items[id].deleted:
        return JSONResponse(
            status_code=HTTPStatus.NOT_MODIFIED,
            content={"message": "not modified"},
        )

    if updates.name is not None:
        items[id].name = updates.name
    if updates.price is not None:
        items[id].price = updates.price

    return items[id].serialize(id)


@app.delete("/item/{id}")
def delete_item(id: int):
    if id in items:
        items[id].deleted = True
