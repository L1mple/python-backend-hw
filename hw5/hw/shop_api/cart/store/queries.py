from sqlalchemy.orm import Session
from typing import Iterable
from .models import CartDB, CartItemDB, CartEntity, CartInfo, CartItemInfo
from shop_api.item.store.models import ItemDB

def create(db: Session) -> CartEntity:
    db_cart = CartDB()
    db.add(db_cart)
    db.commit()
    db.refresh(db_cart)
    return CartEntity(id=db_cart.id, info=CartInfo(items=[], price=0.0))

def add(cart_id: int, item_entity, db: Session) -> CartEntity:
    db_cart = db.query(CartDB).filter(CartDB.id == cart_id).first()
    if not db_cart:
        return None
    
    # Vérifie que l'item existe en base
    db_item = db.query(ItemDB).filter(ItemDB.id == item_entity.id).first()
    if not db_item:
        return None
    
    existing_item = db.query(CartItemDB).filter(
        CartItemDB.cart_id == cart_id, 
        CartItemDB.item_id == item_entity.id
    ).first()
    
    if existing_item:
        existing_item.quantity += 1
    else:
        new_item = CartItemDB(cart_id=cart_id, item_id=item_entity.id, quantity=1)
        db.add(new_item)
    
    db.commit()
    return get_one(cart_id, db)

def delete(id: int, db: Session) -> None:
    db_cart = db.query(CartDB).filter(CartDB.id == id).first()
    if db_cart:
        # Supprime d'abord les items du panier
        db.query(CartItemDB).filter(CartItemDB.cart_id == id).delete()
        db.delete(db_cart)
        db.commit()

def get_one(id: int, db: Session) -> CartEntity | None:
    from shop_api.item.store.models import ItemDB
    db_cart = db.query(CartDB).filter(CartDB.id == id).first()
    if not db_cart:
        return None
    
    total_price = 0.0
    cart_items = []
    
    for cart_item in db_cart.items:
        item = cart_item.item
        if item:  # Vérification de sécurité
            item_total = item.price * cart_item.quantity
            total_price += item_total
            cart_items.append(CartItemInfo(
                id=item.id, 
                name=item.name, 
                quantity=cart_item.quantity, 
                available=not item.deleted
            ))
    
    return CartEntity(id=db_cart.id, info=CartInfo(items=cart_items, price=total_price))

def get_many(db: Session, offset: int = 0, limit: int = 10, 
             min_price: float = None, max_price: float = None, 
             min_quantity: int = None, max_quantity: int = None) -> Iterable[CartEntity]:
    
    query = db.query(CartDB)
    
    # Applique les filtres au niveau de la requête SQL pour plus d'efficacité
    if min_price is not None or max_price is not None:
        # Sous-requête pour les paniers avec prix dans la plage
        from sqlalchemy import func
        subquery = db.query(CartItemDB.cart_id).join(ItemDB).group_by(CartItemDB.cart_id)
        
        if min_price is not None:
            subquery = subquery.having(func.sum(ItemDB.price * CartItemDB.quantity) >= min_price)
        if max_price is not None:
            subquery = subquery.having(func.sum(ItemDB.price * CartItemDB.quantity) <= max_price)
        
        query = query.filter(CartDB.id.in_(subquery))
    
    db_carts = query.offset(offset).limit(limit).all()
    
    for db_cart in db_carts:
        cart_entity = get_one(db_cart.id, db)
        if not cart_entity:
            continue
            
        # Filtres supplémentaires au niveau application
        total_quantity = sum(item.quantity for item in cart_entity.info.items)
        
        if min_quantity is not None and total_quantity < min_quantity:
            continue
        if max_quantity is not None and total_quantity > max_quantity:
            continue
            
        yield cart_entity