"""Тестовый скрипт для проверки интеграции PostgreSQL"""
import asyncio
from database import AsyncSessionLocal, create_tables
from data import item_queries
from data.models import ItemInfo


async def test_database():
    """Тестирует CRUD операции с базой данных"""

    # Создаем таблицы (если еще не созданы)
    await create_tables()
    print("✓ Таблицы созданы/проверены")

    # Создаем сессию
    async with AsyncSessionLocal() as session:
        # 1. Создание товара
        item_info = ItemInfo(name="Laptop", price=1500.0, deleted=False)
        item_entity = await item_queries.add(session, item_info)
        await session.commit()
        print(f"✓ Создан товар: {item_entity}")

        # 2. Получение товара
        retrieved_item = await item_queries.get_one(session, item_entity.id)
        print(f"✓ Получен товар: {retrieved_item}")

        # 3. Обновление товара
        updated_info = ItemInfo(name="Gaming Laptop", price=2000.0, deleted=False)
        updated_item = await item_queries.update(session, item_entity.id, updated_info)
        await session.commit()
        print(f"✓ Обновлен товар: {updated_item}")

        # 4. Получение списка товаров
        items = await item_queries.get_many(session, offset=0, limit=10)
        print(f"✓ Получен список товаров ({len(items)} шт.)")

        # 5. Частичное обновление (patch)
        from data.models import PatchItemInfo
        patch_info = PatchItemInfo(price=1800.0)
        patched_item = await item_queries.patch(session, item_entity.id, patch_info)
        await session.commit()
        print(f"✓ Частично обновлен товар: {patched_item}")

        # 6. Мягкое удаление
        deleted_item = await item_queries.delete(session, item_entity.id)
        await session.commit()
        print(f"✓ Удален товар: {deleted_item}")

        # 7. Проверка, что товар помечен как удаленный
        items_without_deleted = await item_queries.get_many(session, show_deleted=False)
        items_with_deleted = await item_queries.get_many(session, show_deleted=True)
        print(f"✓ Товары без удаленных: {len(items_without_deleted)}")
        print(f"✓ Товары с удаленными: {len(items_with_deleted)}")

    print("\n✅ Все тесты пройдены успешно!")


if __name__ == "__main__":
    asyncio.run(test_database())
