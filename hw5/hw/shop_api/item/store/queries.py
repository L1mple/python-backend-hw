from sqlalchemy.orm import Session
from typing import Iterable
from .models import ItemDB, ItemEntity, ItemInfo, PatchItemInfo

def add(info: ItemInfo, db: Session) -> ItemEntity:
    db_item = ItemDB(name=info.name, price=info.price, deleted=info.deleted)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return ItemEntity(id=db_item.id, info=ItemInfo(name=db_item.name, price=db_item.price, deleted=db_item.deleted))

def delete(id: int, db: Session) -> None:
    db_item = db.query(ItemDB).filter(ItemDB.id == id).first()
    if db_item:
        db.delete(db_item)
        db.commit()

def get_one(id: int, db: Session) -> ItemEntity | None:
    db_item = db.query(ItemDB).filter(ItemDB.id == id).first()
    if not db_item:
        return None
    return ItemEntity(id=db_item.id, info=ItemInfo(name=db_item.name, price=db_item.price, deleted=db_item.deleted))

def get_many(db: Session, offset: int = 0, limit: int = 10, min_price: float = None, max_price: float = None, show_deleted: bool = False) -> Iterable[ItemEntity]:
    query = db.query(ItemDB)
    if min_price is not None:
        query = query.filter(ItemDB.price >= min_price)
    if max_price is not None:
        query = query.filter(ItemDB.price <= max_price)
    if not show_deleted:
        query = query.filter(ItemDB.deleted == False)
    db_items = query.offset(offset).limit(limit).all()
    for db_item in db_items:
        yield ItemEntity(id=db_item.id, info=ItemInfo(name=db_item.name, price=db_item.price, deleted=db_item.deleted))

def update(id: int, info: ItemInfo, db: Session) -> ItemEntity | None:
    db_item = db.query(ItemDB).filter(ItemDB.id == id).first()
    if not db_item:
        return None
    db_item.name = info.name
    db_item.price = info.price
    db_item.deleted = info.deleted
    db.commit()
    db.refresh(db_item)
    return ItemEntity(id=db_item.id, info=ItemInfo(name=db_item.name, price=db_item.price, deleted=db_item.deleted))

def patch(id: int, patch_info: PatchItemInfo, db: Session) -> ItemEntity | None:
    db_item = db.query(ItemDB).filter(ItemDB.id == id).first()
    if not db_item:
        return None
    if patch_info.name is not None:
        db_item.name = patch_info.name
    if patch_info.price is not None:
        db_item.price = patch_info.price
    db.commit()
    db.refresh(db_item)
    return ItemEntity(id=db_item.id, info=ItemInfo(name=db_item.name, price=db_item.price, deleted=db_item.deleted))