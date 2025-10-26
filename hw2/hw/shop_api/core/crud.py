from sqlalchemy.orm import Session
from shop_api.core import models, schemas

def create_item(db: Session, data: schemas.ItemCreate):
    item = models.ItemDB(name=data.name, price=data.price, deleted=False)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

def list_items(db: Session):
    return db.query(models.ItemDB).filter(models.ItemDB.deleted == False).all()

def get_item(db: Session, item_id: int):
    return db.query(models.ItemDB).filter(models.ItemDB.id == item_id).first()

def update_item(db: Session, item_id: int, data: schemas.ItemUpdatePatch):
    item = get_item(db, item_id)
    if item is None:
        return None
    if data.name is not None:
        item.name = data.name
    if data.price is not None:
        item.price = data.price
    db.commit()
    db.refresh(item)
    return item

def delete_item(db: Session, item_id: int):
    item = get_item(db, item_id)
    if item:
        item.deleted = True
        db.commit()
    return item

def create_cart(db: Session):
    cart = models.CartDB()
    db.add(cart)
    db.commit()
    db.refresh(cart)
    return cart

def add_item_to_cart(db: Session, cart_id: int, item_id: int):
    cart = db.query(models.CartDB).filter_by(id=cart_id).first()
    if not cart:
        return None
    item = db.query(models.ItemDB).filter_by(id=item_id, deleted=False).first()
    if not item:
        return None
    cart_item = db.query(models.CartItemDB).filter_by(cart_id=cart_id, item_id=item_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = models.CartItemDB(cart_id=cart_id, item_id=item_id, quantity=1)
        db.add(cart_item)
    db.commit()
    db.refresh(cart)
    return cart