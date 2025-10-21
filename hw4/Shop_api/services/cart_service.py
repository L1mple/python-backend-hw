from sqlalchemy.orm import Session
from Shop_api.repositories.cart_repository import CartRepository
from Shop_api.repositories.item_repository import ItemRepository

class CartService:
    def __init__(self, db: Session):
        self.cart_repo = CartRepository(db)
        self.item_repo = ItemRepository(db)

    def create_cart(self):
        return self.cart_repo.create()

    def get_cart(self, cart_id: int):
        return self.cart_repo.get(cart_id)

    def add_item_to_cart(self, cart_id: int, item_id: int, quantity: int = 1):
        item = self.item_repo.get(item_id)
        if not item:
            return None
        return self.cart_repo.add_item(cart_id, item, quantity)
