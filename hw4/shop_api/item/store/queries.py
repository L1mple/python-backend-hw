from typing import Iterable, Optional

from shop_api.item.store.schemas import ItemEntity, ItemInfo, PatchItemInfo
from shop_api.item.store.models import Item
from sqlalchemy.orm import Session


def add(db: Session, info: ItemInfo) -> ItemEntity:
    db_item = Item(name=info.name, price=info.price, deleted=info.deleted)
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return ItemEntity(id=db_item.id, info=ItemInfo.model_validate(db_item))


def delete(db: Session, id: int) -> bool:
    db_item = db.query(Item).filter(Item.id == id).first()
    if db_item:
        db.delete(db_item)
        db.commit()
        return True
    return False


def get_one(db: Session, id: int) -> Optional[ItemEntity]:
    db_item = db.query(Item).filter(Item.id == id).first()
    if db_item:
        return ItemEntity(id=db_item.id, info=ItemInfo.model_validate(db_item))
    return None


def get_many(
    db: Session,
    offset: int = 0,
    limit: int = 10,
    min_price: float = None,
    max_price: float = None,
    show_deleted: bool = False,
) -> Iterable[ItemEntity]:
    query = db.query(Item)

    if min_price is not None:
        query = query.filter(Item.price >= min_price)
    if max_price is not None:
        query = query.filter(Item.price <= max_price)
    if not show_deleted:
        query = query.filter(Item.deleted.is_(False))


    items = query.offset(offset).limit(limit).all()

    return [
        ItemEntity(id=item.id, info=ItemInfo.model_validate(item))
        for item in items
    ]



def update(db: Session, id: int, info: ItemInfo) -> Optional[ItemEntity]:
    db_item = db.query(Item).filter(Item.id == id).first()
    if db_item:
        db_item.name = info.name
        db_item.price = info.price
        db_item.deleted = info.deleted
        db.commit()
        db.refresh(db_item)
        return ItemEntity(id=db_item.id, info=ItemInfo.from_orm(db_item))
    return None


def patch(db: Session, id: int, patch_info: PatchItemInfo) -> Optional[ItemEntity]:
    db_item = db.query(Item).filter(Item.id == id).first()
    if not db_item:
        return None

    if patch_info.name is not None:
        db_item.name = patch_info.name
    if patch_info.price is not None:
        db_item.price = patch_info.price

    db.commit()
    db.refresh(db_item)
    return ItemEntity(id=db_item.id, info=ItemInfo.from_orm(db_item))

