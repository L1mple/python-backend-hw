from http import HTTPStatus
from typing import Annotated, List
import uuid

from fastapi import APIRouter, HTTPException, Query, Response, Depends
from pydantic import NonNegativeFloat, NonNegativeInt, PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload 

from shop_api.db.session import get_db
from shop_api.models.cart import Cart as CartModel, CartOutSchema
from shop_api.models.item import Item as ItemModel 
from shop_api.models.cart_item import CartItem as CartItemModel 


router = APIRouter(prefix="/cart")


@router.post(
        "",
        response_model=CartOutSchema,
        status_code=HTTPStatus.CREATED
)
async def add_cart(
    response: Response,
    db: AsyncSession = Depends(get_db) 
):
    db_cart = CartModel() 
    
    db.add(db_cart)
    await db.commit()
    await db.refresh(db_cart)

    response.headers["Location"] = f"/cart/{db_cart.id}"
    
    return db_cart


@router.get(
    "/{cart_id}",
    response_model=CartOutSchema,
    status_code=HTTPStatus.OK
)
async def get_cart_by_id(
    cart_id: str,
    db: AsyncSession = Depends(get_db)
):
    try:
        cart_uuid = uuid.UUID(cart_id)
    except ValueError:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Invalid cart_id format")

    query = (
        select(CartModel)
        .where(CartModel.id == cart_uuid)
        .options(
            selectinload(CartModel.cart_items) 
            .selectinload(CartItemModel.item) 
        )
    )
    result = await db.execute(query)
    db_cart = result.scalar_one_or_none()

    if db_cart is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Cart with {cart_id=} wasn't found")

    return db_cart


@router.get(
        "",
        response_model=List[CartOutSchema],
        status_code=HTTPStatus.OK
)
async def get_all_carts(
    offset: Annotated[NonNegativeInt, Query()] = 0,
    limit: Annotated[PositiveInt, Query()] = 10,
    min_price: Annotated[NonNegativeFloat, Query()] = None,
    max_price: Annotated[NonNegativeFloat, Query()] = None,
    min_quantity: Annotated[NonNegativeInt, Query()] = None,
    max_quantity: Annotated[NonNegativeInt, Query()] = None,
    db: AsyncSession = Depends(get_db)
):
    query = (
        select(CartModel)
        .options(
            selectinload(CartModel.cart_items)
            .selectinload(CartItemModel.item)
        )
    )
    result = await db.execute(query)
    all_carts_db = result.scalars().unique().all() 

    all_cart_schemas = [CartOutSchema.model_validate(cart) for cart in all_carts_db]

    filtered_carts: List[CartOutSchema] = []
    for cart in all_cart_schemas:
        if min_price is not None and cart.price < min_price:
            continue
        if max_price is not None and cart.price > max_price:
            continue
        
        total_quantity = sum([cart_item.quantity for cart_item in cart.items])
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue

        filtered_carts.append(cart)
    
    return filtered_carts[offset: offset + limit]


@router.post(
        "/{cart_id}/add/{item_id}",
        response_model=CartOutSchema,
        status_code=HTTPStatus.OK
)
async def add_item_to_cart(
    cart_id: str,
    item_id: str, 
    db: AsyncSession = Depends(get_db)
):
    try:
        cart_uuid = uuid.UUID(cart_id)
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        raise HTTPException(HTTPStatus.NOT_FOUND, "Invalid cart_id or item_id format")

    item_query = select(ItemModel).where(
        ItemModel.id == item_uuid,
        ItemModel.deleted == False
    )
    db_item = (await db.execute(item_query)).scalar_one_or_none()
    
    if db_item is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Item (product) with {item_id=} wasn't found or was deleted")

    cart_query = (
        select(CartModel)
        .where(CartModel.id == cart_uuid)
        .options(selectinload(CartModel.cart_items)) 
    )
    db_cart = (await db.execute(cart_query)).scalar_one_or_none()

    if db_cart is None:
        raise HTTPException(HTTPStatus.NOT_FOUND, f"Cart with {cart_id=} wasn't found")

    existing_cart_item: CartItemModel | None = None
    for cart_item in db_cart.cart_items:
        if cart_item.item_id == item_uuid:
            existing_cart_item = cart_item
            break
    
    if existing_cart_item:
        existing_cart_item.quantity += 1
    else:
        new_cart_item = CartItemModel(
            cart_id=cart_uuid,
            item_id=item_uuid,
            quantity=1
        )
        db.add(new_cart_item)
    
    await db.commit()
    
    return await get_cart_by_id(cart_id, db)
