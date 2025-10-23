from sqlalchemy.orm import Session
from typing import List, Optional
from . import models

class CartQueries:
    @staticmethod
    def create_cart(db: Session) -> models.Cart:
        db_cart = models.Cart()
        db.add(db_cart)
        db.commit()
        db.refresh(db_cart)
        return db_cart

    @staticmethod
    def get_cart(db: Session, cart_id: int) -> Optional[models.Cart]:
        return db.query(models.Cart).filter(models.Cart.id == cart_id).first()

    @staticmethod
    def get_all_carts(db: Session) -> List[models.Cart]:
        return db.query(models.Cart).all()

    @staticmethod
    def add_item_to_cart(db: Session, cart_id: int, item_id: int) -> Optional[models.Cart]:
        cart = CartQueries.get_cart(db, cart_id)
        if not cart:
            return None
        
        item = ItemQueries.get_item(db, item_id)
        if not item or item.deleted:
            return None
        
        cart_item = db.query(models.CartItem).filter(
            models.CartItem.cart_id == cart_id, 
            models.CartItem.item_id == item_id
        ).first()
        
        if cart_item:
            cart_item.quantity += 1
        else:
            cart_item = models.CartItem(cart_id=cart_id, item_id=item_id, quantity=1)
            db.add(cart_item)
        
        db.commit()
        db.refresh(cart)
        return cart

class ItemQueries:
    @staticmethod
    def create_item(db: Session, name: str, price: float) -> models.Item:
        db_item = models.Item(name=name, price=price)
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    @staticmethod
    def get_item(db: Session, item_id: int) -> Optional[models.Item]:
        return db.query(models.Item).filter(models.Item.id == item_id).first()

    @staticmethod
    def get_items(
        db: Session,
        offset: int = 0,
        limit: int = 10,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        show_deleted: bool = False
    ) -> List[models.Item]:
        query = db.query(models.Item)
        
        if not show_deleted:
            query = query.filter(models.Item.deleted == False)
        
        if min_price is not None:
            query = query.filter(models.Item.price >= min_price)
        
        if max_price is not None:
            query = query.filter(models.Item.price <= max_price)
        
        return query.offset(offset).limit(limit).all()

    @staticmethod
    def update_item(db: Session, item_id: int, name: str, price: float) -> Optional[models.Item]:
        db_item = ItemQueries.get_item(db, item_id)
        if db_item and not db_item.deleted:
            db_item.name = name
            db_item.price = price
            db.commit()
            db.refresh(db_item)
            return db_item
        return None

    @staticmethod
    def patch_item(db: Session, item_id: int, **kwargs) -> Optional[models.Item]:
        db_item = ItemQueries.get_item(db, item_id)
        if db_item and not db_item.deleted:
            for field, value in kwargs.items():
                if hasattr(db_item, field) and field != 'deleted':
                    setattr(db_item, field, value)
            db.commit()
            db.refresh(db_item)
            return db_item
        return None

    @staticmethod
    def delete_item(db: Session, item_id: int) -> bool:
        db_item = ItemQueries.get_item(db, item_id)
        if db_item:
            db_item.deleted = True
            db.commit()
            return True
        return False