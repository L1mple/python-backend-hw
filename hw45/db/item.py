from typing import List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from sqlalchemy import Column, Integer, String, Boolean, Numeric
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from db.init import Base


# === Доменные модели (без привязки к БД) ===


@dataclass
class Item:
    """Доменная модель товара"""

    id: Optional[int] = None
    name: str = ""
    price: float = 0
    deleted: bool = False


# === SQLAlchemy модели (для мапинга с БД) ===


class ItemOrm(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    price = Column(Numeric, nullable=False)
    deleted = Column(Boolean, default=func.now())


# === Мапперы (преобразование между доменными моделями и ORM) ===


class ItemMapper:
    """Маппер для преобразования между Item и ItemOrm"""

    @staticmethod
    def to_domain(orm_item: ItemOrm) -> Item:
        """Преобразование ORM модели в доменную"""
        return Item(
            id=orm_item.id,
            name=orm_item.name,
            price=orm_item.price,
            deleted=orm_item.deleted,
        )

    @staticmethod
    def to_orm(
        domain_user: Item,
        orm_user: Optional[ItemOrm] = None,
    ) -> ItemOrm:
        """Преобразование доменной модели в ORM"""
        if orm_user is None:
            orm_user = ItemOrm()

        orm_user.name = domain_user.name
        orm_user.price = domain_user.price
        orm_user.deleted = domain_user.deleted

        return orm_user


# === Абстрактные интерфейсы репозиториев ===


class ItemRepositoryInterface(ABC):
    """Интерфейс репозитория товаров"""

    @abstractmethod
    def create(self, item: Item) -> Item:
        pass

    @abstractmethod
    def find_by_id(self, item_id: int) -> Optional[Item]:
        pass

    @abstractmethod
    def get_all(self) -> List[Item]:
        pass

    @abstractmethod
    def update(self, item: Item) -> Item:
        pass

    @abstractmethod
    def delete(self, item_id: int) -> None:
        pass


# === Конкретные реализации репозиториев ===


class SqlAlchemyItemRepository(ItemRepositoryInterface):
    """SQLAlchemy реализация репозитория товаров"""

    def __init__(self, session: Session):
        self.session = session

    # is_commit используется для возможности демонстрации различных уровней изоляции транзакций в тестах
    def create(self, item: Item, is_commit = True) -> Item:
        orm_item = ItemMapper.to_orm(item)
        self.session.add(orm_item)
        if is_commit:
            self.session.commit()
        return ItemMapper.to_domain(orm_item)

    def find_by_id(self, item_id: int) -> Optional[Item]:
        orm_item = (
            self.session.query(ItemOrm).filter_by(id=item_id).first()
        )
        return ItemMapper.to_domain(orm_item) if orm_item else None

    def get_all(self) -> List[Item]:
        orm_items = self.session.query(ItemOrm).all()
        return [ItemMapper.to_domain(orm_item) for orm_item in orm_items]

    def update(self, item: Item) -> Item:
        orm_item = self.session.query(ItemOrm).filter_by(id=item.id).first()

        ItemMapper.to_orm(item, orm_item)
        self.session.commit()
        return ItemMapper.to_domain(orm_item)

    def delete(self, item_id: int) -> None:
        orm_item = self.session.query(ItemOrm).filter_by(id=item_id).first()
        if not orm_item:
            raise ValueError(f"Item with id {item_id} not found")

        orm_item.deleted = True
        self.session.commit()


# === Сервисы для бизнес-логики ===


class ItemService:
    """Сервис для работы с товарами"""

    def __init__(self, item_repo: ItemRepositoryInterface):
        self.item_repo = item_repo

    def create_item(self, name: str, price: int) -> Item:
        """Создание нового товара с валидацией"""
        item = Item(name=name, price=price)
        return self.item_repo.create(item)
    
    def get_items(self) -> List[Item]:
        """Получение всех товаров"""
        return self.item_repo.get_all()

    def get_item(self, item_id: int) -> Item:
        """Получение товара с проверкой существования"""
        item = self.item_repo.find_by_id(item_id)
        if not item:
            return None
        return item

    def update_item(self, item: Item) -> Item:
        return self.item_repo.update(item)
    
    def delete_item(self, item_id: int):
        self.item_repo.delete(item_id=item_id)