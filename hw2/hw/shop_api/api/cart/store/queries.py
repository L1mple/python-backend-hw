from sqlalchemy.orm import Session
from typing import Iterable
from decimal import Decimal
from itertools import count
from shop_api.database import get_db
from shop_api.database.models import Order, User, Product
from shop_api.database.crud import (
    get_order, get_orders, create_order, update_order, delete_order,
    get_user, get_product
)
from shop_api.database.schemas import OrderCreate, UserCreate, ProductCreate
from .models import CartEntity, CartInfo, CardItem


def create(info: CartInfo) -> CartEntity:
    with next(get_db()) as db:
        user_create = UserCreate(
            email=f"cart_{next(count())}@temp.com",
            name=f"Cart {next(count())}",
            age=18
        )
        db_user = User(
            email=user_create.email,
            name=user_create.name,
            age=user_create.age
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        total_price = Decimal('0')
        for item in info.items:
            product = get_product(db, item.id)
            if product and product.in_stock:
                order_create = OrderCreate(
                    user_id=db_user.id,
                    product_id=item.id,
                    quantity=item.quantity,
                    status='pending'
                )
                order = create_order(db, order_create)
                total_price += order.total_price

        return CartEntity(
            id=db_user.id,
            info=CartInfo(
                items=[CardItem(
                    id=item.id,
                    name=item.name,
                    quantity=item.quantity,
                    available=item.available
                ) for item in info.items],
                price=total_price
            )
        )


def get_one(id: int) -> CartEntity | None:
    with next(get_db()) as db:
        orders = get_orders(db, user_id=id, status='pending')
        if not orders:
            return None

        return CartEntity.from_orders(orders)


def get_list(
    offset: int = 0,
    limit: int = 10,
    min_price: float | None = None,
    max_price: float | None = None,
    min_quantity: int | None = None,
    max_quantity: int | None = None
) -> Iterable[CartEntity]:
    with next(get_db()) as db:
        orders = get_orders(db, status='pending')

        user_orders = {}
        for order in orders:
            if order.user_id not in user_orders:
                user_orders[order.user_id] = []
            user_orders[order.user_id].append(order)

        carts = []
        for user_id, user_order_list in user_orders.items():
            total_price = sum(order.total_price for order in user_order_list)
            total_quantity = sum(order.quantity for order in user_order_list)

            if min_price is not None and total_price < Decimal(str(min_price)):
                continue
            if max_price is not None and total_price > Decimal(str(max_price)):
                continue
            if min_quantity is not None and total_quantity < min_quantity:
                continue
            if max_quantity is not None and total_quantity > max_quantity:
                continue

            items = [CardItem(
                id=order.product.id,
                name=order.product.name,
                quantity=order.quantity,
                available=order.product.in_stock
            ) for order in user_order_list]

            carts.append(CartEntity(
                id=user_id,
                info=CartInfo(
                    items=items,
                    price=total_price
                )
            ))

        return carts[offset:offset+limit]


def add_item_to_cart(cart_id: int, item_id: int) -> CartEntity | None:
    with next(get_db()) as db:
        user = get_user(db, cart_id)
        if not user:
            return None

        product = get_product(db, item_id)
        if not product or not product.in_stock:
            return None

        existing_orders = get_orders(db, user_id=cart_id, product_id=item_id, status='pending')

        if existing_orders:
            existing_order = existing_orders[0]
            existing_order.quantity += 1
            existing_order.total_price = product.price * existing_order.quantity
            db.commit()
            db.refresh(existing_order)
        else:
            order_create = OrderCreate(
                user_id=cart_id,
                product_id=item_id,
                quantity=1,
                status='pending'
            )
            create_order(db, order_create)

        orders = get_orders(db, user_id=cart_id, status='pending')
        return CartEntity.from_orders(orders)

