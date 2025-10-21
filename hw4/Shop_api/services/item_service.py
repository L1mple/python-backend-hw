from sqlalchemy.orm import Session
from Shop_api.repositories.item_repository import ItemRepository
from Shop_api.schemas import ItemCreate

class ItemService:
    def __init__(self, db: Session):
        self.repo = ItemRepository(db)

    def create_item(self, data: ItemCreate):
        return self.repo.create(name=data.name, price=data.price)

    def get_item(self, item_id: int):
        return self.repo.get(item_id)

    def list_items(self, offset: int = 0, limit: int = 10):
        return self.repo.list(offset=offset, limit=limit)

    def update_item(self, item_id: int, data: ItemCreate):
        return self.repo.update(item_id, name=data.name, price=data.price)

    def delete_item(self, item_id: int):
        return self.repo.delete(item_id)
