from dataclasses import dataclass
from decimal import Decimal
from typing import List
from shop_api.database.models import Order, User, Product


@dataclass
class CardItem:
    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class CartInfo:
    items: list[CardItem]
    price: Decimal


@dataclass(slots=True)
class CartEntity:
    id: int
    info: CartInfo

    @staticmethod
    def from_order(order: Order) -> 'CartEntity':
        return CartEntity(
            id=order.id,
            info=CartInfo(
                items=[CardItem(
                    id=order.product.id,
                    name=order.product.name,
                    quantity=order.quantity,
                    available=order.product.in_stock
                )],
                price=order.total_price
            )
        )

    @staticmethod
    def from_orders(orders: List[Order]) -> 'CartEntity':
        if not orders:
            return None
        user_orders = {}
        total_price = Decimal('0')

        for order in orders:
            if order.user_id not in user_orders:
                user_orders[order.user_id] = []

            user_orders[order.user_id].append(order)
            total_price += order.total_price

        first_user_orders = orders
        items = []

        for order in first_user_orders:
            items.append(CardItem(
                id=order.product.id,
                name=order.product.name,
                quantity=order.quantity,
                available=order.product.in_stock
            ))

        return CartEntity(
            id=first_user_orders[0].user_id,
            info=CartInfo(
                items=items,
                price=total_price
            )
        )
