from typing import List, Optional
from dataclasses import dataclass
from abc import ABC, abstractmethod

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session
from sqlalchemy.sql import func


# === Доменные модели (без привязки к БД) ===

@dataclass
class User:
    """Доменная модель пользователя"""
    id: Optional[int] = None
    email: str = ""
    name: str = ""
    age: int = 0


# === SQLAlchemy модели (для мапинга с БД) ===

Base = declarative_base()


class UserOrm(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


# === Мапперы (преобразование между доменными моделями и ORM) ===

class UserMapper:
    """Маппер для преобразования между User и UserOrm"""

    @staticmethod
    def to_domain(orm_user: UserOrm) -> User:
        """Преобразование ORM модели в доменную"""
        return User(
            id=orm_user.id,
            email=orm_user.email,
            name=orm_user.name,
            age=orm_user.age
        )

    @staticmethod
    def to_orm(
        domain_user: User,
        orm_user: Optional[UserOrm] = None,
    ) -> UserOrm:
        """Преобразование доменной модели в ORM"""
        if orm_user is None:
            orm_user = UserOrm()

        orm_user.email = domain_user.email
        orm_user.name = domain_user.name
        orm_user.age = domain_user.age

        return orm_user


# === Абстрактные интерфейсы репозиториев ===

class UserRepositoryInterface(ABC):
    """Интерфейс репозитория пользователей"""

    @abstractmethod
    def create(self, user: User) -> User:
        pass

    @abstractmethod
    def find_by_id(self, user_id: int) -> Optional[User]:
        pass

    @abstractmethod
    def find_by_email(self, email: str) -> Optional[User]:
        pass

    @abstractmethod
    def get_all(self) -> List[User]:
        pass

    @abstractmethod
    def update(self, user: User) -> User:
        pass


# === Конкретные реализации репозиториев ===

class SqlAlchemyUserRepository(UserRepositoryInterface):
    """SQLAlchemy реализация репозитория пользователей"""

    def __init__(self, session: Session):
        self.session = session

    def create(self, user: User) -> User:
        orm_user = UserMapper.to_orm(user)
        self.session.add(orm_user)
        self.session.flush()  # Получаем ID без коммита
        return UserMapper.to_domain(orm_user)

    def find_by_id(self, user_id: int) -> Optional[User]:
        orm_user = self.session.query(UserOrm).filter_by(id=user_id).first()
        return UserMapper.to_domain(orm_user) if orm_user else None

    def find_by_email(self, email: str) -> Optional[User]:
        orm_user = self.session.query(UserOrm).filter_by(email=email).first()
        return UserMapper.to_domain(orm_user) if orm_user else None

    def get_all(self) -> List[User]:
        orm_users = self.session.query(UserOrm).order_by(UserOrm.created_at).all()
        return [UserMapper.to_domain(orm_user) for orm_user in orm_users]

    def update(self, user: User) -> User:
        orm_user = self.session.query(UserOrm).filter_by(id=user.id).first()
        if not orm_user:
            raise ValueError(f"User with id {user.id} not found")

        UserMapper.to_orm(user, orm_user)
        self.session.flush()
        return UserMapper.to_domain(orm_user)


# === Сервисы для бизнес-логики ===

class UserService:
    """Сервис для работы с пользователями"""

    def __init__(self, user_repo: UserRepositoryInterface):
        self.user_repo = user_repo

    def create_user(self, email: str, name: str, age: int) -> User:
        """Создание нового пользователя с валидацией"""
        existing_user = self.user_repo.find_by_email(email)
        if existing_user:
            raise ValueError(f"User with email {email} already exists")

        if age < 0:
            raise ValueError("Age cannot be negative")

        user = User(email=email, name=name, age=age)
        return self.user_repo.create(user)

    def get_user_with_validation(self, user_id: int) -> User:
        """Получение пользователя с проверкой существования"""
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise ValueError(f"User with id {user_id} not found")
        return user
