from typing import Optional, List
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from shop_api.models import (
    Cart,
    Item,
    CartItem,
    CartFilterParams,
    ItemFilterParams,
    NotModifiedError,
    NotFoundError
)


class DB:
    def __init__(self):
        print('---Инициализация соединения с БД---')
        database_url = os.getenv('DATABASE_URL', 'postgresql://shop_user:shop_password@localhost:5432/shop_db')
        self.engine = create_engine(database_url, echo=True)
        self.SessionLocal = sessionmaker(bind=self.engine)
        self._init_db()
        
    def _init_db(self):
        """Инициализация схемы БД"""
        with self.engine.connect() as conn:
            # Создание таблицы items
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS items (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price NUMERIC(10, 2) NOT NULL CHECK (price > 0),
                    deleted BOOLEAN DEFAULT FALSE
                )
            """))
            
            # Создание таблицы carts
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS carts (
                    id SERIAL PRIMARY KEY,
                    price NUMERIC(10, 2) DEFAULT 0 CHECK (price >= 0)
                )
            """))
            
            # Создание таблицы cart_items (связь many-to-many)
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS cart_items (
                    cart_id INTEGER REFERENCES carts(id) ON DELETE CASCADE,
                    item_id INTEGER REFERENCES items(id) ON DELETE CASCADE,
                    quantity INTEGER NOT NULL CHECK (quantity > 0),
                    PRIMARY KEY (cart_id, item_id)
                )
            """))
            
            conn.commit()
    
    def _get_session(self) -> Session:
        return self.SessionLocal()
    
    def _calculate_cart_price(self, session: Session, cart_id: int) -> float:
        """Вычисление общей стоимости корзины"""
        result = session.execute(text("""
            SELECT COALESCE(SUM(ci.quantity * i.price), 0) as total_price
            FROM cart_items ci
            JOIN items i ON ci.item_id = i.id
            WHERE ci.cart_id = :cart_id
        """), {"cart_id": cart_id})
        return float(result.scalar())
    
    def _update_cart_price(self, session: Session, cart_id: int):
        """Обновление цены корзины"""
        total_price = self._calculate_cart_price(session, cart_id)
        session.execute(text("""
            UPDATE carts SET price = :price WHERE id = :cart_id
        """), {"price": total_price, "cart_id": cart_id})

    def create_cart(self) -> Cart:
        session = self._get_session()
        try:
            result = session.execute(text("""
                INSERT INTO carts (price) VALUES (0) RETURNING id
            """))
            cart_id = result.scalar()
            session.commit()
            return Cart(id=cart_id, items=[], price=0.0)
        finally:
            session.close()
    
    def get_cart_by_id(self, cart_id: int) -> Optional[Cart]:
        session = self._get_session()
        try:
            # Получаем информацию о корзине
            cart_result = session.execute(text("""
                SELECT id, price FROM carts WHERE id = :cart_id
            """), {"cart_id": cart_id})
            cart_row = cart_result.fetchone()
            
            if not cart_row:
                return None
            
            # Получаем товары в корзине
            items_result = session.execute(text("""
                SELECT i.id, i.name, ci.quantity, NOT i.deleted as available
                FROM cart_items ci
                JOIN items i ON ci.item_id = i.id
                WHERE ci.cart_id = :cart_id
            """), {"cart_id": cart_id})
            
            cart_items = [
                CartItem(id=row[0], name=row[1], quantity=row[2], available=row[3])
                for row in items_result.fetchall()
            ]
            
            return Cart(id=cart_row[0], items=cart_items, price=float(cart_row[1]))
        finally:
            session.close()
    
    def get_carts(self, params: CartFilterParams) -> List[Cart]:
        session = self._get_session()
        try:
            # Строим динамический запрос
            conditions = []
            query_params = {}
            
            if params.min_price is not None:
                conditions.append("c.price >= :min_price")
                query_params["min_price"] = params.min_price
            if params.max_price is not None:
                conditions.append("c.price <= :max_price")
                query_params["max_price"] = params.max_price
            
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            # Получаем корзины с учетом фильтров по цене
            query = f"""
                SELECT c.id, c.price
                FROM carts c
                {where_clause}
                ORDER BY c.id
                OFFSET :offset LIMIT :limit
            """
            query_params["offset"] = params.offset
            query_params["limit"] = params.limit
            
            cart_results = session.execute(text(query), query_params).fetchall()
            
            carts = []
            for cart_row in cart_results:
                cart_id = cart_row[0]
                
                # Получаем товары для каждой корзины
                items_result = session.execute(text("""
                    SELECT i.id, i.name, ci.quantity, NOT i.deleted as available
                    FROM cart_items ci
                    JOIN items i ON ci.item_id = i.id
                    WHERE ci.cart_id = :cart_id
                """), {"cart_id": cart_id})
                
                cart_items = [
                    CartItem(id=row[0], name=row[1], quantity=row[2], available=row[3])
                    for row in items_result.fetchall()
                ]
                
                # Проверяем фильтры по количеству товаров
                total_quantity = sum(item.quantity for item in cart_items)
                if params.min_quantity is not None and total_quantity < params.min_quantity:
                    continue
                if params.max_quantity is not None and total_quantity > params.max_quantity:
                    continue
                
                carts.append(Cart(id=cart_row[0], items=cart_items, price=float(cart_row[1])))
            
            return carts
        finally:
            session.close()
    
    def add_item_to_cart(self, cart_id: int, item_id: int) -> bool:
        session = self._get_session()
        try:
            # Проверяем существование корзины
            cart_check = session.execute(text("""
                SELECT id FROM carts WHERE id = :cart_id
            """), {"cart_id": cart_id}).fetchone()
            
            # Проверяем существование товара
            item_check = session.execute(text("""
                SELECT id FROM items WHERE id = :item_id
            """), {"item_id": item_id}).fetchone()
            
            if not cart_check or not item_check:
                raise NotFoundError(detail="Корзина и/или товар не найдены")
            
            # Проверяем, есть ли уже этот товар в корзине
            existing_item = session.execute(text("""
                SELECT quantity FROM cart_items 
                WHERE cart_id = :cart_id AND item_id = :item_id
            """), {"cart_id": cart_id, "item_id": item_id}).fetchone()
            
            if existing_item:
                # Увеличиваем количество
                session.execute(text("""
                    UPDATE cart_items 
                    SET quantity = quantity + 1 
                    WHERE cart_id = :cart_id AND item_id = :item_id
                """), {"cart_id": cart_id, "item_id": item_id})
            else:
                # Добавляем новый товар в корзину
                session.execute(text("""
                    INSERT INTO cart_items (cart_id, item_id, quantity)
                    VALUES (:cart_id, :item_id, 1)
                """), {"cart_id": cart_id, "item_id": item_id})
            
            # Обновляем цену корзины
            self._update_cart_price(session, cart_id)
            
            session.commit()
            return True
        finally:
            session.close()
    
    def create_item(self, name: str, price: float) -> Item:
        session = self._get_session()
        try:
            result = session.execute(text("""
                INSERT INTO items (name, price, deleted) 
                VALUES (:name, :price, FALSE) 
                RETURNING id
            """), {"name": name, "price": price})
            item_id = result.scalar()
            session.commit()
            return Item(id=item_id, name=name, price=price, deleted=False)
        finally:
            session.close()

    def get_item_by_id(self, item_id: int) -> Optional[Item]:
        session = self._get_session()
        try:
            result = session.execute(text("""
                SELECT id, name, price, deleted 
                FROM items 
                WHERE id = :item_id AND deleted = FALSE
            """), {"item_id": item_id})
            row = result.fetchone()
            
            if not row:
                return None
            
            return Item(id=row[0], name=row[1], price=float(row[2]), deleted=row[3])
        finally:
            session.close()
    
    def get_items(self, params: ItemFilterParams) -> List[Item]:
        session = self._get_session()
        try:
            conditions = []
            query_params = {}
            
            if not params.show_deleted:
                conditions.append("deleted = FALSE")
            
            if params.min_price is not None:
                conditions.append("price >= :min_price")
                query_params["min_price"] = params.min_price
            
            if params.max_price is not None:
                conditions.append("price <= :max_price")
                query_params["max_price"] = params.max_price
            
            where_clause = ""
            if conditions:
                where_clause = "WHERE " + " AND ".join(conditions)
            
            query = f"""
                SELECT id, name, price, deleted 
                FROM items 
                {where_clause}
                ORDER BY id
                OFFSET :offset LIMIT :limit
            """
            query_params["offset"] = params.offset
            query_params["limit"] = params.limit
            
            result = session.execute(text(query), query_params)
            
            items = [
                Item(id=row[0], name=row[1], price=float(row[2]), deleted=row[3])
                for row in result.fetchall()
            ]
            
            return items
        finally:
            session.close()

    def replace_item(self, item_id: int, new_name: str, new_price: float) -> Item:
        session = self._get_session()
        try:
            # Проверяем существование товара
            check = session.execute(text("""
                SELECT id FROM items WHERE id = :item_id
            """), {"item_id": item_id}).fetchone()
            
            if not check:
                raise NotFoundError("Товар не найден")
            
            # Обновляем товар
            session.execute(text("""
                UPDATE items 
                SET name = :name, price = :price 
                WHERE id = :item_id
            """), {"item_id": item_id, "name": new_name, "price": new_price})
            
            session.commit()
            
            # Получаем обновленный товар
            result = session.execute(text("""
                SELECT id, name, price, deleted FROM items WHERE id = :item_id
            """), {"item_id": item_id})
            row = result.fetchone()
            
            return Item(id=row[0], name=row[1], price=float(row[2]), deleted=row[3])
        finally:
            session.close()

    def edit_item(self, item_id: int, new_name: Optional[str] = None, new_price: Optional[str] = None) -> Item:
        session = self._get_session()
        try:
            # Проверяем существование товара
            result = session.execute(text("""
                SELECT id, name, price, deleted FROM items WHERE id = :item_id
            """), {"item_id": item_id})
            row = result.fetchone()
            
            if not row:
                raise NotFoundError("Товар не найден")
            
            if row[3]:  # deleted
                raise NotModifiedError("Товар удален, его невозможно изменить")
            
            # Обновляем только переданные поля
            updates = []
            params = {"item_id": item_id}
            
            if new_name is not None:
                updates.append("name = :name")
                params["name"] = new_name
            
            if new_price is not None:
                updates.append("price = :price")
                params["price"] = new_price
            
            if updates:
                update_query = f"UPDATE items SET {', '.join(updates)} WHERE id = :item_id"
                session.execute(text(update_query), params)
                session.commit()
            
            # Получаем обновленный товар
            result = session.execute(text("""
                SELECT id, name, price, deleted FROM items WHERE id = :item_id
            """), {"item_id": item_id})
            row = result.fetchone()
            
            return Item(id=row[0], name=row[1], price=float(row[2]), deleted=row[3])
        finally:
            session.close()
    
    def delete_item(self, item_id: int) -> bool:
        session = self._get_session()
        try:
            # Проверяем существование товара
            check = session.execute(text("""
                SELECT id FROM items WHERE id = :item_id
            """), {"item_id": item_id}).fetchone()
            
            if not check:
                raise NotFoundError("Товар не найден")
            
            # Помечаем товар как удаленный
            session.execute(text("""
                UPDATE items SET deleted = TRUE WHERE id = :item_id
            """), {"item_id": item_id})
            
            session.commit()
            return True
        finally:
            session.close()
    
    def close(self):
        print('---Закрытие соединения с БД---')
        if hasattr(self, 'engine'):
            self.engine.dispose()

