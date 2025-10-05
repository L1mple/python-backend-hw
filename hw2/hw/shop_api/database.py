from shop_api.models import Cart, Item

class Shop:
    def __init__(self):
        self.carts: dict = {}
        self.items: dict = {}
        
        self.current_cart_id = 0
        self.current_item_id = 0

