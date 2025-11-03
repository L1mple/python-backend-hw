from typing import Optional
from sqlalchemy.orm import Session
from shop_api.db_models import SessionLocal, Item, Cart, CartItem, init_db


class Storage:
    def __init__(self):
        init_db()

    def _get_db(self) -> Session:
        return SessionLocal()

    def create_item(self, name: str, price: float) -> dict:
        db = self._get_db()
        try:
            new_item = Item(name=name, price=price)
            db.add(new_item)
            db.commit()
            db.refresh(new_item)
            return {"id": new_item.id, "name": new_item.name, "price": new_item.price, "deleted": new_item.deleted}
        finally:
            db.close()

    def get_item(self, item_id: int) -> Optional[dict]:
        db = self._get_db()
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if item:
                return {"id": item.id, "name": item.name, "price": item.price, "deleted": item.deleted}
            return None
        finally:
            db.close()

    def update_item(self, item_id: int, name: Optional[str] = None, price: Optional[float] = None) -> Optional[dict]:
        db = self._get_db()
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None
            if name is not None:
                item.name = name
            if price is not None:
                item.price = price
            db.commit()
            return {"id": item.id, "name": item.name, "price": item.price, "deleted": item.deleted}
        finally:
            db.close()

    def replace_item(self, item_id: int, name: str, price: float) -> Optional[dict]:
        db = self._get_db()
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None
            item.name = name
            item.price = price
            db.commit()
            return {"id": item.id, "name": item.name, "price": item.price, "deleted": item.deleted}
        finally:
            db.close()

    def delete_item(self, item_id: int) -> Optional[dict]:
        db = self._get_db()
        try:
            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                return None
            item.deleted = True
            db.commit()
            return {"id": item.id, "name": item.name, "price": item.price, "deleted": item.deleted}
        finally:
            db.close()

    def get_all_items(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False
    ) -> list[dict]:
        db = self._get_db()
        try:
            query = db.query(Item)
            if not show_deleted:
                query = query.filter(Item.deleted == False)
            if min_price is not None:
                query = query.filter(Item.price >= min_price)
            if max_price is not None:
                query = query.filter(Item.price <= max_price)

            items = query.offset(offset).limit(limit).all()
            return [{"id": i.id, "name": i.name, "price": i.price, "deleted": i.deleted} for i in items]
        finally:
            db.close()

    def create_cart(self) -> int:
        db = self._get_db()
        try:
            new_cart = Cart()
            db.add(new_cart)
            db.commit()
            db.refresh(new_cart)
            return new_cart.id
        finally:
            db.close()

    def get_cart(self, cart_id: int) -> Optional[dict]:
        db = self._get_db()
        try:
            cart = db.query(Cart).filter(Cart.id == cart_id).first()
            if not cart:
                return None

            items_list = []
            total_price = 0.0

            cart_items = db.query(CartItem).filter(CartItem.cart_id == cart_id).all()
            for cart_item in cart_items:
                item = db.query(Item).filter(Item.id == cart_item.item_id).first()
                if item:
                    available = not item.deleted
                    items_list.append({
                        "id": item.id,
                        "name": item.name,
                        "quantity": cart_item.quantity,
                        "available": available
                    })
                    if available:
                        total_price += item.price * cart_item.quantity

            return {"id": cart_id, "items": items_list, "price": total_price}
        finally:
            db.close()

    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        db = self._get_db()
        try:
            cart = db.query(Cart).filter(Cart.id == cart_id).first()
            if not cart:
                return False

            item = db.query(Item).filter(Item.id == item_id).first()
            if not item:
                return False

            cart_item = db.query(CartItem).filter(
                CartItem.cart_id == cart_id,
                CartItem.item_id == item_id
            ).first()

            if cart_item:
                cart_item.quantity += 1
            else:
                cart_item = CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
                db.add(cart_item)

            db.commit()
            return True
        finally:
            db.close()

    def get_all_carts(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        min_quantity: Optional[int] = None,
        max_quantity: Optional[int] = None
    ) -> list[dict]:
        db = self._get_db()
        try:
            carts = db.query(Cart).all()
            result = []

            for cart in carts:
                cart_data = self.get_cart(cart.id)
                if cart_data:
                    if min_price is not None and cart_data['price'] < min_price:
                        continue
                    if max_price is not None and cart_data['price'] > max_price:
                        continue

                    total_quantity = sum(item['quantity'] for item in cart_data['items'])
                    if min_quantity is not None and total_quantity < min_quantity:
                        continue
                    if max_quantity is not None and total_quantity > max_quantity:
                        continue

                    result.append(cart_data)

            return result[offset:offset + limit]
        finally:
            db.close()


storage = Storage()
