import asyncio
import os
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from shop_api.database import Base
from shop_api import db_models

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://shop_user:shop_password@localhost:5445/shop_db"
)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def ensure_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def setup_test_data():
    await ensure_tables()
    async with async_session_maker() as session:
        await session.execute(text("TRUNCATE TABLE cart_items, carts, items RESTART IDENTITY CASCADE"))
        await session.execute(text(
            "INSERT INTO items (name, price, deleted) VALUES ('Test Item', 100.0, false)"
        ))
        await session.commit()
    print("+ Тестовые данные созданы\n")


async def demo_dirty_read_uncommitted():
    """
    ДЕМОНСТРАЦИЯ 1: Попытка Dirty Read при READ UNCOMMITTED
    B PostgreSQL READ UNCOMMITTED работает как READ COMMITTED,
    поэтому dirty reads НЕ происходят даже на этом уровне.
    """
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ 1: READ UNCOMMITTED - Попытка Dirty Read")
    print("=" * 60)
    
    await setup_test_data()
    
    async def transaction_1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
            
            print("T1: Начало транзакции (READ UNCOMMITTED)")
            print("T1: Обновление цены товара с 100.0 на 999.0")
            await session.execute(text("UPDATE items SET price = 999.0 WHERE id = 1"))
            
            print("T1: Ожидание 2 секунды")
            await asyncio.sleep(2)
            
            print("T1: Откат транзакции (ROLLBACK)")
            await session.rollback()
            print("T1: Завершено\n")
    
    async def transaction_2():
        await asyncio.sleep(0.5)
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ UNCOMMITTED"))
            
            print("T2: Начало транзакции (READ UNCOMMITTED)")
            result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
            price = result.scalar()
            print(f"T2: Чтение цены товара: {price}")
            
            if price == 100.0:
                print("T2: + Dirty Read НЕ произошел! Видны только закоммиченные данные (100.0)")
            else:
                print(f"T2: - Dirty Read произошел! Видны незакоммиченные данные ({price})")
            
            await session.commit()
            print("T2: Завершено\n")
    
    await asyncio.gather(transaction_1(), transaction_2())
    print("-" * 50 + "\n")


async def demo_no_dirty_read_committed():
    """
    ДЕМОНСТРАЦИЯ 2: Отсутствие Dirty Read при READ COMMITTED
    При уровне READ COMMITTED dirty reads не происходят.
    """
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ 2: READ COMMITTED - Отсутствие Dirty Read")
    print("=" * 60)
    
    await setup_test_data()
    
    async def transaction_1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            
            print("T1: Начало транзакции (READ COMMITTED)")
            print("T1: Обновление цены товара с 100.0 на 999.0")
            await session.execute(text("UPDATE items SET price = 999.0 WHERE id = 1"))
            
            print("T1: Ожидание 2 секунды")
            await asyncio.sleep(2)
            
            print("T1: Откат транзакции (ROLLBACK)")
            await session.rollback()
            print("T1: Завершено\n")
    
    async def transaction_2():
        await asyncio.sleep(0.5)
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            
            print("T2: Начало транзакции (READ COMMITTED)")
            result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
            price = result.scalar()
            print(f"T2: Чтение цены товара: {price}")
            
            if price == 100.0:
                print("T2: + Dirty Read НЕ произошел! Видны только закоммиченные данные (100.0)")
            else:
                print(f"T2: - Dirty Read произошел! Видны незакоммиченные данные ({price})")
            
            await session.commit()
            print("T2: Завершено\n")
    
    await asyncio.gather(transaction_1(), transaction_2())
    print("-" * 50 + "\n")


async def demo_non_repeatable_read_committed():
    """
    ДЕМОНСТРАЦИЯ 3: Non-Repeatable Read при READ COMMITTED
    При READ COMMITTED одна транзакция может видеть изменения другой.
    """
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ 3: READ COMMITTED - Non-Repeatable Read")
    print("=" * 60)
    
    await setup_test_data()
    
    async def transaction_1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            
            print("T1: Начало транзакции (READ COMMITTED)")
            result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
            price1 = result.scalar()
            print(f"T1: Первое чтение цены: {price1}")
            
            print("T1: Ожидание изменения данных T2")
            await asyncio.sleep(2)
            
            result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
            price2 = result.scalar()
            print(f"T1: Второе чтение цены: {price2}")
            
            if price1 != price2:
                print(f"T1: + Non-Repeatable Read произошел! ({price1} -> {price2})")
            else:
                print("T1: - Non-Repeatable Read НЕ произошел")
            
            await session.commit()
            print("T1: Завершено\n")
    
    async def transaction_2():
        await asyncio.sleep(0.5)
        async with async_session_maker() as session:
            print("T2: Начало транзакции")
            print("T2: Изменение цены товара с 100.0 на 200.0")
            await session.execute(text("UPDATE items SET price = 200.0 WHERE id = 1"))
            await session.commit()
            print("T2: Изменение закоммичено")
            print("T2: Завершено\n")
    
    await asyncio.gather(transaction_1(), transaction_2())
    print("-" * 50 + "\n")


async def demo_no_non_repeatable_read_repeatable():
    """
    ДЕМОНСТРАЦИЯ 4: Отсутствие Non-Repeatable Read при REPEATABLE READ
    При REPEATABLE READ транзакция видит снимок данных на момент начала.
    """
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ 4: REPEATABLE READ - Отсутствие Non-Repeatable Read")
    print("=" * 60)
    
    await setup_test_data()
    
    async def transaction_1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            
            print("T1: Начало транзакции (REPEATABLE READ)")
            result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
            price1 = result.scalar()
            print(f"T1: Первое чтение цены: {price1}")

            print("T1: Ожидание изменения данных T2")
            await asyncio.sleep(2)
            
            result = await session.execute(text("SELECT price FROM items WHERE id = 1"))
            price2 = result.scalar()
            print(f"T1: Второе чтение цены: {price2}")
            
            if price1 == price2:
                print(f"T1: + Non-Repeatable Read НЕ произошел! Виден стабильный снимок ({price1})")
            else:
                print(f"T1: - Non-Repeatable Read произошел ({price1} -> {price2})")
            
            await session.commit()
            print("T1: Завершено\n")
    
    async def transaction_2():
        await asyncio.sleep(0.5)
        async with async_session_maker() as session:
            print("T2: Начало транзакции")
            print("T2: Изменение цены товара с 100.0 на 200.0")
            await session.execute(text("UPDATE items SET price = 200.0 WHERE id = 1"))
            await session.commit()
            print("T2: Изменение закоммичено")
            print("T2: Завершено\n")
    
    await asyncio.gather(transaction_1(), transaction_2())
    print("-" * 50 + "\n")


async def demo_phantom_read_repeatable():
    """
    ДЕМОНСТРАЦИЯ 5: Phantom Reads при REPEATABLE READ
    B PostgreSQL REPEATABLE READ предотвращает phantom reads
    """
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ 5: REPEATABLE READ - Phantom Reads")
    print("=" * 60)
    
    await setup_test_data()
    
    async def transaction_1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            
            print("T1: Начало транзакции (REPEATABLE READ)")
            result = await session.execute(text("SELECT COUNT(*) FROM items WHERE deleted = false"))
            count1 = result.scalar()
            print(f"T1: Первое чтение количества товаров: {count1}")

            print("T1: Ожидание пока T2 добавит новый товар")
            await asyncio.sleep(2)
            
            result = await session.execute(text("SELECT COUNT(*) FROM items WHERE deleted = false"))
            count2 = result.scalar()
            print(f"T1: Второе чтение количества товаров: {count2}")
            
            if count1 == count2:
                print(f"T1: + Phantom Read НЕ произошел! Количество стабильно ({count1})")
            else:
                print(f"T1: - Phantom Read произошел! ({count1} -> {count2})")
            
            await session.commit()
            print("T1: Завершено\n")
    
    async def transaction_2():
        await asyncio.sleep(0.5)
        async with async_session_maker() as session:
            print("T2: Начало транзакции")
            print("T2: Добавление нового товара")
            await session.execute(text(
                "INSERT INTO items (name, price, deleted) VALUES ('New Item', 150.0, false)"
            ))
            await session.commit()
            print("T2: Новый товар добавлен и закоммичен")
            print("T2: Завершено\n")
    
    await asyncio.gather(transaction_1(), transaction_2())
    print("-" * 50 + "\n")


async def demo_no_phantom_read_serializable():
    """
    ДЕМОНСТРАЦИЯ 6: Отсутствие Phantom Reads при SERIALIZABLE
    При SERIALIZABLE транзакции полностью изолированы.
    """
    print("=" * 60)
    print("ДЕМОНСТРАЦИЯ 6: SERIALIZABLE - Отсутствие Phantom Reads")
    print("=" * 60)
    
    await setup_test_data()
    
    async def transaction_1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            
            print("T1: Начало транзакции (SERIALIZABLE)")
            result = await session.execute(text("SELECT COUNT(*) FROM items WHERE deleted = false"))
            count1 = result.scalar()
            print(f"T1: Первое чтение количества товаров: {count1}")

            print("T1: Ожидание попытки добавления нового товара T2")
            await asyncio.sleep(2)
            
            result = await session.execute(text("SELECT COUNT(*) FROM items WHERE deleted = false"))
            count2 = result.scalar()
            print(f"T1: Второе чтение количества товаров: {count2}")
            
            if count1 == count2:
                print(f"T1: + Phantom Read НЕ произошел! Количество стабильно ({count1})")
            else:
                print(f"T1: - Phantom Read произошел! ({count1} -> {count2})")
            
            await session.commit()
            print("T1: Завершено\n")
    
    async def transaction_2():
        await asyncio.sleep(0.5)
        async with async_session_maker() as session:
            try:
                await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                print("T2: Начало транзакции (SERIALIZABLE)")
                print("T2: Попытка добавить новый товар")
                await session.execute(text(
                    "INSERT INTO items (name, price, deleted) VALUES ('New Item', 150.0, false)"
                ))
                await session.commit()
                print("T2: Товар успешно добавлен")
                print("T2: Завершено\n")
            except Exception as e:
                print(f"T2: + Транзакция не смогла завершиться из-за конфликта сериализации")
                print(f"T2: Ошибка: {type(e).__name__}")
                await session.rollback()
                print("T2: Завершено с откатом\n")
    
    await asyncio.gather(transaction_1(), transaction_2())
    print("-" * 50 + "\n")


async def main():
    print("\n")
    print("=" * 50)
    print("=" * 50)
    print("ДЕМОНСТРАЦИЯ УРОВНЕЙ ИЗОЛЯЦИИ ТРАНЗАКЦИЙ")
    print("=" * 50)
    print("=" * 50)
    print("\n")
    
    try:
        await demo_dirty_read_uncommitted()
        await asyncio.sleep(1)
        
        await demo_no_dirty_read_committed()
        await asyncio.sleep(1)
        
        await demo_non_repeatable_read_committed()
        await asyncio.sleep(1)
        
        await demo_no_non_repeatable_read_repeatable()
        await asyncio.sleep(1)
        
        await demo_phantom_read_repeatable()
        await asyncio.sleep(1)
        
        await demo_no_phantom_read_serializable()
        
        print("\n")
        print("=" * 50)
        print("=" * 50)
        print("ДЕМОНСТРАЦИЯ ЗАВЕРШЕНА")
        print("=" * 50)
        print("=" * 50)
        print("\n")
        
    except Exception as e:
        print(f"\n!!! Ошибка: {e}")
        print("Убедитесь, что PostgreSQL запущен и доступен по адресу:")
        print(f"  {DATABASE_URL}")
        raise
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
