from sqlalchemy.orm import Session
from Shop_api.repositories.cart_repository import CartRepository
from Shop_api.repositories.item_repository import ItemRepository
from Shop_api.models import Cart, CartItem, Item

class CartService:
    def __init__(self, db: Session):
        self.db = db

    def create_cart(self) -> Cart:
        cart = Cart(total_price=0.0)
        self.db.add(cart)
        self.db.commit()
        self.db.refresh(cart)
        return cart

    def get_cart(self, cart_id: int) -> Cart | None:
        cart = (
            self.db.query(Cart)
            .filter(Cart.id == cart_id)
            .first()
        )
        return cart

    def add_item_to_cart(self, cart_id: int, item_id: int, quantity: int = 1) -> Cart | None:
        cart = self.get_cart(cart_id)
        item = self.db.query(Item).filter(Item.id == item_id, Item.deleted == False).first()

        if not cart or not item:
            return None

    
        cart_item = (
            self.db.query(CartItem)
            .filter(CartItem.cart_id == cart_id, CartItem.item_id == item_id)
            .first()
        )
        if cart_item:
            cart_item.quantity += quantity
        else:
            cart_item = CartItem(cart_id=cart_id, item_id=item_id, quantity=quantity)
            self.db.add(cart_item)

        # Met à jour le total du panier
        cart.total_price += item.price * quantity

        self.db.commit()
        self.db.refresh(cart)
        return cart