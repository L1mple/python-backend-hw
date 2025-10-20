from http import HTTPStatus
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from sqlalchemy.orm import Session
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt

from shop_api.cart import store
from shop_api.cart.contracts import CartResponse
import shop_api.item.store
from database import get_db

router = APIRouter(prefix="/cart")


@router.post("/", status_code=HTTPStatus.CREATED)
async def post_cart(
    response: Response,
    db: Session = Depends(get_db)
) -> CartResponse:
    entity = store.create(db)
    response.headers["location"] = f"/cart/{entity.id}"
    return CartResponse.from_entity(entity)


@router.get(
    "/{id}",
    responses={
        HTTPStatus.OK: {
            "description": "Successfully returned requested cart",
        },
        HTTPStatus.NOT_FOUND: {
            "description": "Failed to return requested cart as one was not found",
        },
    },
)
async def get_cart_by_id(
    id: int,
    db: Session = Depends(get_db)
):
    entity = store.get_one(id, db)

    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Request resource /cart/{id} was not found",
        )

    return CartResponse.from_entity(entity)


@router.get("/")
async def get_cart_list(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] | None = None,
    max_price: Annotated[NonNegativeFloat, Query()] | None = None,
    min_quantity: Annotated[NonNegativeFloat, Query()] | None = None,
    max_quantity: Annotated[NonNegativeFloat, Query()] | None = None,
    db: Session = Depends(get_db)
):
    return [
        CartResponse.from_entity(e)
        for e in store.get_many(db, offset, limit, min_price, max_price, min_quantity, max_quantity)
    ]


@router.post("/{cart_id}/add/{item_id}")
async def add_to_cart(
    cart_id: int, 
    item_id: int,
    db: Session = Depends(get_db)
):
    # Récupère l'item depuis la base
    item_entity = shop_api.item.store.get_one(item_id, db)
    
    if not item_entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Item {item_id} not found",
        )

    # Ajoute l'item au panier
    entity = store.add(cart_id, item_entity, db)
    
    if not entity:
        raise HTTPException(
            HTTPStatus.NOT_FOUND,
            f"Cart {cart_id} not found",
        )

    return CartResponse.from_entity(entity)


@router.delete("/{id}")
async def delete_cart(
    id: int,
    db: Session = Depends(get_db)
) -> Response:
    store.delete(id, db)
    return Response("", status_code=HTTPStatus.NO_CONTENT)