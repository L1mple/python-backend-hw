from sqlalchemy.orm import Session
from Shop_api.models import Item

class ItemRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str, price: float) -> Item:
        item = Item(name=name, price=price)
        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)
        return item

    def get(self, item_id: int) -> Item | None:
        return self.db.query(Item).filter(Item.id == item_id, Item.deleted == False).first()

    def list(self, offset: int = 0, limit: int = 10):
        return self.db.query(Item).filter(Item.deleted == False).offset(offset).limit(limit).all()

    def update(self, item_id: int, name: str | None = None, price: float | None = None) -> Item | None:
        item = self.db.query(Item).filter(Item.id == item_id, Item.deleted == False).first()
        if not item:
            return None
        if name is not None:
            item.name = name
        if price is not None:
            item.price = price
        self.db.commit()
        self.db.refresh(item)
        return item

    def delete(self, item_id: int) -> bool:
        item = self.db.query(Item).filter(Item.id == item_id).first()
        if not item or item.deleted:
            return False
        item.deleted = True
        self.db.commit()
        return True
