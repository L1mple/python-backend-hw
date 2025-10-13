from dataclasses import dataclass, field
from typing import List, Dict, Optional
import uuid


@dataclass(slots=True)
class ItemData:
    """Represents an item in the shop with basic information."""

    id: int
    name: str
    price: float
    deleted: bool = False


@dataclass(slots=True)
class ItemsData:
    """Container for multiple items data."""

    items: List[ItemData] = field(default_factory=list)


@dataclass(slots=True)
class ItemnInCartData:
    """Represents an item in a shopping cart with quantity and availability."""

    id: int
    name: str
    quantity: int
    available: bool


@dataclass(slots=True)
class CartData:
    """Represents a shopping cart with items and total price."""

    id: int
    items: List[ItemnInCartData] = field(default_factory=list)
    price: float = 0.0


@dataclass(slots=True)
class IdDataGen:
    """ID generator utility class."""

    id: int

    def gen_id():
        """Generate a new unique ID using UUID4."""
        id = int(uuid.uuid4())
        return IdDataGen(id=id)


@dataclass(slots=True)
class Storage:
    """Main storage class for managing items and carts."""

    items: Dict[int, ItemData] = field(default_factory=dict)
    carts: Dict[int, CartData] = field(default_factory=dict)
    id_generator = IdDataGen

    def add_item(self, name: str, price: float) -> ItemData:
        """Add a new item to storage and return it."""
        item_id = self.id_generator.gen_id().id
        item = ItemData(id=item_id, name=name, price=price)
        self.items[item_id] = item
        return item

    def create_cart(self) -> CartData:
        """Create a new empty cart and return it."""
        cart_id = self.id_generator.gen_id().id
        cart = CartData(id=cart_id)
        self.carts[cart_id] = cart
        return cart

    def get_item(self, id,) -> ItemData:
        """Get item by ID."""
        item = self.items[id]
        if item.deleted:
            raise KeyError(f"Item {id} not found") 
        return item

    def get_cart(self, id) -> CartData:
        """Get cart by ID."""
        cart = self.carts[id]
        return cart

    def get_items(self,
                offset: int = 0,
                limit: int = 10, 
                min_price: float = None,
                max_price: float = None,
                show_deleted: bool = False) -> list[ItemsData]:
        """Get all items."""
        items = list(self.items.values())
        if not show_deleted: 
            items = [item for item in items if not item.deleted]
        if min_price is not None:
            items = [item for item in items if item.price >=min_price]
        if max_price is not None:
            items = [item for item in items if item.price <= max_price] 

        return items[offset:offset+limit]

    def get_carts(self,
                offset: int = 0,
                limit: int = 10, 
                min_price: float = None,
                max_price: float = None,
                min_quantity: int = None,
                max_quantity: int = None) -> list[CartData]:
        carts = list(self.carts.values())
        
        if min_price is not None:
            carts = [cart for cart in carts if cart.price >= min_price]
        if max_price is not None:
            carts = [cart for cart in carts if cart.price <= max_price]
        
        if min_quantity is not None or max_quantity is not None:
            def get_total_quantity(cart):
                return sum(item.quantity for item in cart.items)
            
            if min_quantity is not None:
                carts = [cart for cart in carts if get_total_quantity(cart) >= min_quantity]
            if max_quantity is not None:
                carts = [cart for cart in carts if get_total_quantity(cart) <= max_quantity]

        return carts[offset:offset+limit]


    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        """Add item to cart, updating quantity if item already exists. Returns True if successful."""
        if cart_id not in self.carts or item_id not in self.items:
            return False

        cart = self.carts[cart_id]
        item = self.items[item_id]

        for cart_item in cart.items:
            if cart_item.id == item_id:
                cart_item.quantity += 1
                break
        else:
            cart_item = ItemnInCartData(
                id=item.id, name=item.name, quantity=1, available=not item.deleted
            )
            cart.items.append(cart_item)

        cart.price = sum(
            self.items[cart_item.id].price * cart_item.quantity
            for cart_item in cart.items
            if cart_item.available and cart_item.id in self.items
        )

        return True
    
    def put_item(self, item_id: int, name: str, price: float)-> ItemData:
        item = self.items[item_id]
        item.name = name
        item.price = price
        return item 

    def patch_item(self, item_id: int, name: Optional[str], price: Optional[float])-> ItemData:
        item = self.items[item_id]
        if name is not None:
            item.name = name
        if price is not None: 
            item.price = price
        return item 
    
    def soft_delete_item(self, item_id:int):
        item = self.items[item_id]
        item.deleted = True
        return item

# Глобальный экземпляр storage
local_storage = Storage()