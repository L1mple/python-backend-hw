from sqlalchemy.orm import Session
from store import models

def create_item(db: Session, name: str, price: float):
    item = models.Item(name=name, price=price)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def get_item(db: Session, item_id: int):
    return db.query(models.Item).filter(models.Item.id == item_id).first()

def list_items(db: Session):
    return db.query(models.Item).all()

def update_item(db: Session, item_id: int, name: str, price: float):
    item = get_item(db, item_id)
    if not item:
        return None
    item.name = name
    item.price = price
    db.commit()
    db.refresh(item)
    return item

def patch_item(db: Session, item_id: int, data: dict):
    item = get_item(db, item_id)
    if not item:
        return None
    for k, v in data.items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item

def delete_item(db: Session, item_id: int):
    item = get_item(db, item_id)
    if not item:
        return False
    item.deleted = True
    db.commit()
    return True

# --- CARTS ---

def create_cart(db: Session):
    cart = models.Cart()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart

def get_cart(db: Session, cart_id: int):
    return db.query(models.Cart).filter(models.Cart.id == cart_id).first()

def list_carts(db: Session):
    return db.query(models.Cart).all()

def add_to_cart(db: Session, cart_id: int, item_id: int):
    cart = get_cart(db, cart_id)
    item = get_item(db, item_id)
    if not cart or not item:
        return None

    existing = db.query(models.CartItem).filter(
        models.CartItem.cart_id == cart_id,
        models.CartItem.item_id == item_id
    ).first()

    if existing:
        existing.quantity += 1
    else:
        db.add(models.CartItem(cart_id=cart_id, item_id=item_id, quantity=1))

    db.commit()
    recalc_cart_price(db, cart_id)
    db.refresh(cart)
    return cart

def recalc_cart_price(db: Session, cart_id: int):
    cart = get_cart(db, cart_id)
    total = sum(ci.quantity * ci.item.price for ci in cart.items if not ci.item.deleted)
    cart.total_price = total
    db.commit()
