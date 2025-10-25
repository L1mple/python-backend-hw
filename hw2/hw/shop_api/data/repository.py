from typing import Optional, List

from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session
from sqlalchemy.sql.functions import coalesce

from .models import ItemOrm, CartItemOrm, CartOrm
from .schemas import Item, PatchItem, Cart
from .mappers import ItemMapper, CartMapper

class ItemRepository:
    def __init__(self, session : Session):
        self.session = session

    def create(self, item : Item) -> Item:
        orm_item = ItemMapper.to_orm(item)
        self.session.add(orm_item)
        self.session.flush()
        return ItemMapper.to_domain(orm_item)

    def find_by_id(self, item_id : int) -> Optional[Item]:
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        return ItemMapper.to_domain(orm_item) if orm_item else None

    def find_by_name(self, item_name : str) -> Optional[Item]:
        orm_item = self.session.query(ItemOrm).filter_by(name=item_name).first()
        return ItemMapper.to_domain(orm_item) if orm_item else None

    def get_items(
        self, offset : int = 0, limit : int = 10,
        min_price : Optional[float] = None, max_price : Optional[float] = None,
        show_deleted : bool = False
    ) -> List[Item]:
        orm_items = self.session.query(ItemOrm)
        if not show_deleted:
            orm_items = orm_items.filter_by(deleted=False)
        if min_price is not None:
            orm_items = orm_items.filter(ItemOrm.price >= min_price)
        if max_price is not None:
            orm_items = orm_items.filter(ItemOrm.price <= max_price)
        orm_items = orm_items.order_by(ItemOrm.id).offset(offset).limit(limit).all()
        items = [ItemMapper.to_domain(orm_item) for orm_item in orm_items]
        return items

    def patch(self, item_id : int, patch_item : PatchItem) -> Item:
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        if orm_item is None:
            raise ValueError(f"Item with id {item_id} not found")
        if patch_item.name is not None:
            orm_item.name = patch_item.name
        if patch_item.price is not None:
            orm_item.price = patch_item.price
        self.session.flush()
        return ItemMapper.to_domain(orm_item)

    def update(self, item_id : int, item : Item) -> Item:
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        if not orm_item:
            raise ValueError(f"Item with id {item_id} not found")
        orm_item = ItemMapper.to_orm(item, orm_item)
        self.session.flush()
        return ItemMapper.to_domain(orm_item)

    def delete(self, item_id : int) -> None:
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        if orm_item:
            orm_item.deleted = True
        self.session.flush()


class CartRepository:
    def __init__(self, session : Session):
        self.session = session

    def create(self):
        orm_cart = CartOrm()
        self.session.add(orm_cart)
        self.session.flush()
        return CartMapper.to_domain(orm_cart)

    def find_by_id(self, cart_id : int) -> Optional[Cart]:
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        return CartMapper.to_domain(orm_cart) if orm_cart else None

    def get_carts(
        self, offset : int = 0, limit : int = 10,
        min_price : Optional[float] = None, max_price : Optional[float] = None,
        max_quantity : Optional[int] = None, min_quantity : Optional[int] = None
    ) -> List[Cart]:
        price_comp = CartItemOrm.quantity * ItemOrm.price
        price_comp = case((ItemOrm.deleted, 0.0), else_=price_comp)
        total_price = coalesce(func.sum(price_comp), 0.0)
        total_quantity = coalesce(func.sum(CartItemOrm.quantity), 0)

        joined_orm_carts = self.session.query(
            CartOrm.id.label("cart_id"), total_quantity.label("total_qty"), total_price.label("total_price")
        ).join(
            CartItemOrm, CartItemOrm.cart_id == CartOrm.id
        ).join(
            ItemOrm, CartItemOrm.item_id == ItemOrm.id
        ).group_by(CartOrm.id)

        having = []
        if max_price is not None:
            having.append(total_price <= max_price)
        if min_price is not None:
            having.append(total_price >= min_price)
        if max_quantity is not None:
            having.append(total_quantity <= max_quantity)
        if min_quantity is not None:
            having.append(total_quantity >= min_quantity)
        if having:
            joined_orm_carts = joined_orm_carts.having(and_(*having))

        cart_ids = [cart.cart_id for cart in joined_orm_carts]
        if not cart_ids:
            return []

        orm_carts = self.session.query(CartOrm).filter(CartOrm.id.in_(cart_ids)).offset(offset).limit(limit).all()
        carts = [CartMapper.to_domain(orm_cart) for orm_cart in orm_carts]
        return carts

    def add_to_cart(self, cart_id : int, item_id : int) -> Cart:
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        if orm_cart is None:
            raise ValueError(f"Cart with id {cart_id} not found")
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        if orm_item is None:
            raise ValueError(f"Item with id {item_id} not found")

        cart_item_orm = self.session.query(CartItemOrm).filter_by(cart_id=cart_id, item_id=item_id).first()
        if cart_item_orm:
            cart_item_orm.quantity = cart_item_orm.quantity + 1
        else:
            cart_item_orm = CartItemOrm(cart_id=cart_id, item_id=item_id, quantity=1)
            self.session.add(cart_item_orm)

        self.session.flush()
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        return CartMapper.to_domain(orm_cart)

    def delete(self, cart_id : int) -> None:
        orm_cart = self.session.query(CartOrm).filter_by(id=cart_id).first()
        if orm_cart is None:
            return
        self.session.delete(orm_cart)
        self.session.flush()
