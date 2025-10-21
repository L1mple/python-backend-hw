from sqlalchemy.orm import Session
from Shop_api.models import Cart, CartItem, Item

class CartRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self) -> Cart:
        cart = Cart()
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    def get(self, cart_id: int) -> Cart | None:
        return self.db.query(Cart).filter(Cart.id == cart_id).first()

    def add_item(self, cart_id: int, item: Item, quantity: int = 1) -> Cart | None:
        cart = self.get(cart_id)
        if not cart or item.deleted:
            return None

        cart_item = self.db.query(CartItem).filter(
            CartItem.cart_id == cart.id, CartItem.item_id == item.id
        ).first()

        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(cart_id=cart.id, item_id=item.id, quantity=quantity)
            self.db.add(cart_item)


        cart.total_price = sum(ci.quantity * ci.item.price for ci in cart.items)
        self.db.commit()
        self.db.refresh(cart)
        return cart
