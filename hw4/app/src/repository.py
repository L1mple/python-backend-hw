from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional, Sequence

from sqlalchemy import select, func, literal_column, join
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.models import Item, Cart, CartItem

class ItemRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str, price: float) -> Item:
        item = Item(name=name, price=Decimal(str(price)))
        self.session.add(item)
        self._commit()
        self.session.refresh(item)
        return item

    def get(self, item_id: int) -> Optional[Item]:
        return self.session.get(Item, item_id)

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False,
    ) -> Sequence[Item]:
        stmt = select(Item)
        if not show_deleted:
            stmt = stmt.where(Item.deleted.is_(False))
        if min_price is not None:
            stmt = stmt.where(Item.price >= Decimal(str(min_price)))
        if max_price is not None:
            stmt = stmt.where(Item.price <= Decimal(str(max_price)))
        stmt = stmt.order_by(Item.id).offset(offset).limit(limit)
        return self.session.execute(stmt).scalars().all()

    def replace(self, item_id: int, *, name: str, price: float) -> Optional[Item]:
        item = self.get(item_id)
        if not item:
            return None
        item.name = name
        item.price = Decimal(str(price))
        self._commit()
        self.session.refresh(item)
        return item

    def patch(self, item_id: int, *, name: Optional[str] = None, price: Optional[float] = None) -> Optional[Item]:
        item = self.get(item_id)
        if not item:
            return None
        if name is not None:
            item.name = name
        if price is not None:
            item.price = Decimal(str(price))
        self._commit()
        self.session.refresh(item)
        return item

    def soft_delete(self, item_id: int) -> bool:
        item = self.get(item_id)
        if not item:
            return False
        item.deleted = True
        self._commit()
        return True

    def _commit(self):
        try:
            self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise e

@dataclass
class CartItemDTO:
    item_id: int
    name: str
    price: float
    quantity: int

@dataclass
class CartDTO:
    id: int
    total_price: float
    total_quantity: int
    items: list[CartItemDTO]

class CartRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self) -> Cart:
        cart = Cart()
        self.session.add(cart)
        self.session.commit()
        self.session.refresh(cart)
        return cart

    def _load_cart_items(self, cart_id: int) -> list[CartItemDTO]:
        stmt = (
            select(CartItem.item_id, Item.name, Item.price, CartItem.quantity)
            .join(Item, Item.id == CartItem.item_id)
            .where(CartItem.cart_id == cart_id, Item.deleted.is_(False))
            .order_by(CartItem.item_id)
        )
        rows = self.session.execute(stmt).all()
        return [
            CartItemDTO(
                item_id=r.item_id,
                name=r.name,
                price=float(r.price),
                quantity=r.quantity,
            )
            for r in rows
        ]

    def _calc_totals(self, items: list[CartItemDTO]) -> tuple[float, int]:
        total_qty = sum(i.quantity for i in items)
        total_price = sum(i.price * i.quantity for i in items)
        return float(total_price), int(total_qty)

    def get(self, cart_id: int) -> Optional[CartDTO]:
        cart = self.session.get(Cart, cart_id)
        if not cart:
            return None
        items = self._load_cart_items(cart_id)
        total_price, total_qty = self._calc_totals(items)
        return CartDTO(id=cart.id, total_price=total_price, total_quantity=total_qty, items=items)

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None,
    ) -> list[CartDTO]:
        agg = (
            select(
                Cart.id.label("cart_id"),
                func.coalesce(func.sum((Item.price * CartItem.quantity)), 0).label("total_price"),
                func.coalesce(func.sum(CartItem.quantity), 0).label("total_qty"),
            )
            .select_from(join(Cart, CartItem, Cart.id == CartItem.cart_id, isouter=True)
                         .join(Item, Item.id == CartItem.item_id, isouter=True))
            .where((Item.deleted.is_(False)) | (Item.id.is_(None)))
            .group_by(Cart.id)
        )
        if min_price is not None:
            agg = agg.having(func.coalesce(func.sum((Item.price * CartItem.quantity)), 0) >= Decimal(str(min_price)))
        if max_price is not None:
            agg = agg.having(func.coalesce(func.sum((Item.price * CartItem.quantity)), 0) <= Decimal(str(max_price)))
        if min_quantity is not None:
            agg = agg.having(func.coalesce(func.sum(CartItem.quantity), 0) >= int(min_quantity))
        if max_quantity is not None:
            agg = agg.having(func.coalesce(func.sum(CartItem.quantity), 0) <= int(max_quantity))

        agg = agg.order_by(literal_column("cart_id")).offset(offset).limit(limit)
        rows = self.session.execute(agg).all()
        result: list[CartDTO] = []
        for r in rows:
            items = self._load_cart_items(r.cart_id)
            total_price = float(r.total_price or 0)
            total_qty = int(r.total_qty or 0)
            result.append(CartDTO(id=r.cart_id, total_price=total_price, total_quantity=total_qty, items=items))
        return result

    def add_item(self, cart_id: int, item_id: int) -> Optional[CartDTO]:
        cart = self.session.get(Cart, cart_id)
        if not cart:
            return None
        item = self.session.get(Item, item_id)
        if not item or item.deleted:
            return None

        link = self.session.get(CartItem, {"cart_id": cart_id, "item_id": item_id})
        if link:
            link.quantity = int(link.quantity) + 1
        else:
            self.session.add(CartItem(cart_id=cart_id, item_id=item_id, quantity=1))
        self.session.commit()
        return self.get(cart_id)
