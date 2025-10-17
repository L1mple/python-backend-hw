from typing import List, Optional
from datetime import datetime
from sqlmodel import SQLModel, Field, Session, select


# === ActiveRecord модели ===

class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, max_length=255)
    name: str = Field(max_length=255)
    age: int = Field(ge=0)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)

    # === ActiveRecord методы ===

    @classmethod
    def create(cls, session: Session, email: str, name: str, age: int) -> "User":
        """Создание нового пользователя"""
        user = cls(email=email, name=name, age=age)
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    @classmethod
    def find_by_id(cls, session: Session, user_id: int) -> Optional["User"]:
        """Поиск пользователя по ID"""
        return session.get(cls, user_id)

    @classmethod
    def find_by_email(cls, session: Session, email: str) -> Optional["User"]:
        """Поиск пользователя по email"""
        statement = select(cls).where(cls.email == email)
        return session.exec(statement).first()

    @classmethod
    def get_all_with_stats(cls, session: Session) -> List[dict]:
        """Получение всех пользователей со статистикой заказов"""
        statement = select(cls).order_by(cls.created_at)
        users = session.exec(statement).all()

        result = []
        for user in users:
            result.append({
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "age": user.age,
                "order_count": 0
            })
        return result

    def update_age(self, session: Session, new_age: int) -> "User":
        """Обновление возраста пользователя"""
        self.age = new_age
        self.updated_at = datetime.utcnow()
        session.add(self)
        session.commit()
        session.refresh(self)
        return self

    def to_dict(self) -> dict:
        """Преобразование в словарь для вывода"""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "age": self.age,
            "created_at": self.created_at
        }
