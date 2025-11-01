from .schemas import Cart, CreateItem, Item, ItemCart, PatchItem, UpdateItem


class DataBase:
    def __init__(self):
        # Симуляция базы данных
        self.db_items: list[Item] = []
        self.db_carts: list[Cart] = []
        # Счетчики
        self.counter_ids_items: int = 0
        self.counter_ids_carts: int = 0

    def create_item(self, item: CreateItem):
        new_item = Item(id=self.counter_ids_items, name=item.name, price=item.price)
        self.db_items.append(new_item)
        self.counter_ids_items += 1
        return new_item

    def create_cart(self):
        new_cart = Cart(id=self.counter_ids_carts)
        self.db_carts.append(new_cart)
        self.counter_ids_carts += 1
        return new_cart

    def get_cart_by_id(self, cart_id: int):
        if cart_id >= len(self.db_carts):
            return None
        else:
            return self.db_carts[cart_id]

    def get_item_by_id(self, item_id: int):
        if item_id >= len(self.db_items):
            return None
        elif self.db_items[item_id].deleted:
            return None
        else:
            return self.db_items[item_id]

    def update_item(self, item_id: int, item: UpdateItem):
        if item_id >= len(self.db_items):
            return None
        else:
            self.db_items[item_id] = Item(
                id=item_id,
                name=item.name,
                price=item.price,
            )
            return self.db_items[item_id]

    def patch_item(self, item_id: int, item: PatchItem):
        if item_id >= len(self.db_items):
            return None, 404

        if (
            item_id == self.db_items[item_id].id
            and item.name == self.db_items[item_id].name
            and item.price == self.db_items[item_id].price
        ) or self.db_items[item_id].deleted:
            return self.db_items[item_id], 304

        self.db_items[item_id] = Item(
            id=item_id,
            name=item.name or self.db_items[item_id].name,
            price=item.price or self.db_items[item_id].price,
        )
        return self.db_items[item_id], 200

    def delete_item(self, item_id: int):
        if item_id >= len(self.db_items):
            return None
        else:
            self.db_items[item_id] = Item(
                id=item_id,
                name=self.db_items[item_id].name,
                price=self.db_items[item_id].price,
                deleted=True,
            )
            return self.db_items[item_id]

    def get_items(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float = None,
        max_price: float = None,
        show_deleted: bool = False,
    ):
        if offset is not None and offset < 0:
            return None, 422
        if limit is not None and limit <= 0:
            return None, 422
        if min_price is not None and min_price < 0:
            return None, 422
        if max_price is not None and max_price < 0:
            return None, 422
        items_copy = self.db_items.copy()
        if not show_deleted:
            for item in self.db_items:
                if item.deleted:
                    items_copy.remove(item)
        if min_price is not None:
            items_copy = [item for item in items_copy if item.price >= min_price]
        if max_price is not None:
            items_copy = [item for item in items_copy if item.price <= max_price]
        return items_copy[offset : offset + limit], 200

    def get_carts(
        self,
        offset: int = 0,
        limit: int = 10,
        min_price: float = None,
        max_price: float = None,
        min_quantity: int = None,
        max_quantity: int = None,
    ):
        if offset is not None and offset < 0:
            return None, 422
        if limit is not None and limit <= 0:
            return None, 422
        if min_price is not None and min_price < 0:
            return None, 422
        if max_price is not None and max_price < 0:
            return None, 422
        if min_quantity is not None and min_quantity < 0:
            return None, 422
        if max_quantity is not None and max_quantity < 0:
            return None, 422
        carts_copy = self.db_carts.copy()
        if min_price is not None:
            carts_copy = [cart for cart in carts_copy if cart.price >= min_price]
        if max_price is not None:
            carts_copy = [cart for cart in carts_copy if cart.price <= max_price]
        if min_quantity is not None:
            carts_copy = [cart for cart in carts_copy if len(cart.items) >= min_quantity]
        if max_quantity is not None:
            carts_copy = [cart for cart in carts_copy if len(cart.items) <= max_quantity]
        return carts_copy[offset : offset + limit], 200

    def add_item_to_cart(self, cart_id: int, item_id: int):
        if cart_id >= len(self.db_carts):
            return None, 404
        if item_id >= len(self.db_items):
            return None, 404
        item_to_add = self.get_item_by_id(item_id)
        is_item_addded = False
        for item in self.db_carts[cart_id].items:
            if item.id == item_id:
                item.quantity += 1
                self.db_carts[cart_id].price += item_to_add.price
                is_item_addded = True
                break
        if is_item_addded == False:
            self.db_carts[cart_id].items.append(
                ItemCart(
                    id=item_id,
                    name=item_to_add.name,
                    quantity=1,
                    available=item_to_add.deleted,
                )
            )
            self.db_carts[cart_id].price += item_to_add.price
        return self.db_carts[cart_id], 200


# Симуляция базы данных
db = DataBase()
