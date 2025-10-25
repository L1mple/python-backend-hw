from sqlalchemy.orm import Session
from fastapi import Depends

from .pg import SessionLocal
from .repository import ItemRepository, CartRepository

def get_session():
    db : Session = SessionLocal()
    try:
        yield db
        db.commit()
    except:
        db.rollback()
        raise
    finally:
        db.close()

def get_item_repo(db : Session = Depends(get_session)) -> ItemRepository:
    return ItemRepository(db)

def get_cart_repo(db : Session = Depends(get_session)) -> CartRepository:
    return CartRepository(db)
