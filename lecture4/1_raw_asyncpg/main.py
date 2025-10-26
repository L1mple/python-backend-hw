import asyncpg
from typing import Optional, List


class UserRepository:
    """Простой репозиторий для работы с пользователями через asyncpg"""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.pool: Optional[asyncpg.Pool] = None

    async def initialize(self):
        """Инициализация пула соединений"""
        self.pool = await asyncpg.create_pool(self.connection_string, min_size=2, max_size=10)

    async def close(self):
        """Закрытие пула"""
        if self.pool:
            await self.pool.close()

    async def create_user(self, email: str, name: str, age: int) -> int:
        """Создание нового пользователя"""
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(
                "INSERT INTO users (email, name, age) VALUES ($1, $2, $3) RETURNING id",
                email, name, age
            )
            return row['id']

    async def get_user_by_id(self, user_id: int) -> Optional[dict]:
        """Получение пользователя по ID"""
        async with self.pool.acquire() as connection:
            row = await connection.fetchrow(
                "SELECT id, email, name, age, created_at FROM users WHERE id = $1",
                user_id
            )
            return dict(row) if row else None

    async def update_user_age(self, user_id: int, new_age: int) -> bool:
        """Обновление возраста пользователя"""
        async with self.pool.acquire() as connection:
            result = await connection.execute(
                "UPDATE users SET age = $1 WHERE id = $2",
                new_age, user_id
            )
            return result.split()[-1] == '1'

    async def get_users_with_orders(self) -> List[dict]:
        """Получение пользователей с количеством их заказов (JOIN запрос)"""
        async with self.pool.acquire() as connection:
            rows = await connection.fetch("""
                SELECT
                    u.id, u.name, u.email,
                    COUNT(o.id) as order_count,
                    COALESCE(SUM(o.total_price), 0) as total_spent
                FROM users u
                LEFT JOIN orders o ON u.id = o.user_id
                GROUP BY u.id, u.name, u.email
                ORDER BY total_spent DESC
            """)
            return [dict(row) for row in rows]
