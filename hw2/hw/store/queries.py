from sqlalchemy.orm import Session

from .db import get_session
from .models import (
    Cart,
    Item,
    SqlAlchemyCartRepository,
    SqlAlchemyCartItemRepository,
    SqlAlchemyItemRepository,
    ItemMapper,
    ItemOrm,
)


## Cart methods
def post_cart() -> int:
    with get_session() as session:
        return SqlAlchemyCartRepository(session).post_cart()


def get_cart(id: int) -> Cart | None:
    with get_session() as session:
        return SqlAlchemyCartRepository(session).get_cart(id)


def get_carts_list(
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        min_quantity: int | None = None,
        max_quantity: int | None = None,
) -> list[Cart]:
    with get_session() as session:
        return SqlAlchemyCartRepository(session).get_carts_list(
            offset=offset,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            min_quantity=min_quantity,
            max_quantity=max_quantity,
        )


def add_item_to_cart(cart_id: int, item_id: int) -> None:
    with get_session() as session:
        SqlAlchemyCartItemRepository(session).add_item_to_cart(cart_id, item_id)


## Item methods
def post_item(name: str, price: float, deleted: bool = False) -> int:
    with get_session() as session:
        return SqlAlchemyItemRepository(session).post_item(name=name, price=price, deleted=deleted)


def get_item(item_id: int) -> Item | None:
    with get_session() as session:
        return SqlAlchemyItemRepository(session).get_item(item_id)


def get_item_including_deleted(item_id: int) -> Item | None:
    with get_session() as session:
        orm = session.get(ItemOrm, item_id)
        if orm is None:
            return None
        return ItemMapper.to_domain(orm)


def get_items_list(
        offset: int = 0,
        limit: int = 10,
        min_price: float | None = None,
        max_price: float | None = None,
        show_deleted: bool = False
) -> list[Item]:
    with get_session() as session:
        return SqlAlchemyItemRepository(session).get_items_list(
            offset=offset,
            limit=limit,
            min_price=min_price,
            max_price=max_price,
            show_deleted=show_deleted,
        )


def put_item(item_id: int, name: str, price: float) -> Item | None:
    with get_session() as session:
        return SqlAlchemyItemRepository(session).put_item(item_id=item_id, name=name, price=price)


def patch_item(item_id: int, name: str | None = None, price: float | None = None) -> Item | None:
    with get_session() as session:
        return SqlAlchemyItemRepository(session).patch_item(item_id=item_id, name=name, price=price)


def delete_item(item_id: int) -> None:
    with get_session() as session:
        SqlAlchemyItemRepository(session).delete_item(item_id)
