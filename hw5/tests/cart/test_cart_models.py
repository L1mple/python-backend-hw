from shop_api.cart.store.models import Cart, CartItem
from shop_api.item.store.models import Item


def test_cart_and_cartitem_relationship(session):
    cart = Cart(price=0.0)
    item = Item(name="Pen", price=2.5)
    session.add_all([cart, item])
    session.commit()

    cart_item = CartItem(cart_id=cart.id, item_id=item.id, name="Pen", quantity=3)
    session.add(cart_item)
    session.commit()

    loaded_cart = session.query(Cart).first()
    assert len(loaded_cart.items) == 1
    assert loaded_cart.items[0].quantity == 3
    assert loaded_cart.items[0].item.name == "Pen"
