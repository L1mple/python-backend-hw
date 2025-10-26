"""
ДЕМОНСТРАЦИЯ: Phantom Reads (Фантомное чтение)

Phantom Read возникает когда транзакция выполняет один и тот же запрос дважды,
но между выполнениями другая транзакция добавляет или удаляет строки,
которые удовлетворяют условию запроса.

Проблема: количество строк в результате запроса изменяется в рамках одной транзакции.

Уровни изоляции:
- REPEATABLE READ: в PostgreSQL предотвращает Phantom Reads (в отличие от SQL стандарта!)
- SERIALIZABLE: гарантированно предотвращает Phantom Reads

ВАЖНО: В PostgreSQL REPEATABLE READ уже предотвращает Phantom Reads благодаря MVCC!
Это отличается от SQL стандарта.
"""
import asyncio
from sqlalchemy import select, func
from db_setup import Account, get_async_session, init_database, set_isolation_level


async def transaction_1_repeatable_read():
    async with get_async_session() as session:
        async with session.begin():
            await set_isolation_level(session, "REPEATABLE READ")
            print("[T1] Начало транзакции (REPEATABLE READ)")
            
            result = await session.execute(
                select(func.count(Account.id)).where(Account.balance > 500)
            )
            count_1 = result.scalar()
            print(f"[T1] Первое чтение: найдено {count_1} счетов")
            
            await asyncio.sleep(1)
            
            result = await session.execute(
                select(func.count(Account.id)).where(Account.balance > 500)
            )
            count_2 = result.scalar()
            print(f"[T1] Второе чтение: найдено {count_2} счетов")
            
            if count_1 == count_2:
                print("[T1] REPEATABLE READ предотвращает Phantom Reads")


async def transaction_2_insert_account():
    await asyncio.sleep(0.5)
    
    async with get_async_session() as session:
        async with session.begin():
            print("[T2] Начало транзакции")
            
            new_account = Account(id=4, name="David", balance=800.00)
            session.add(new_account)
            print("[T2] Добавили новый счет David")
            
            await session.commit()
            print("[T2] COMMIT")


async def transaction_1_serializable():
    async with get_async_session() as session:
        async with session.begin():
            await set_isolation_level(session, "SERIALIZABLE")
            print("[T1] Начало транзакции (SERIALIZABLE)")
            
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            print(f"[T1] Прочитали Alice: ${account.balance}")
            
            await asyncio.sleep(1)
            
            account.balance += 100
            print(f"[T1] Обновляем баланс Alice")
            
            try:
                await session.commit()
                print("[T1] COMMIT успешен")
            except Exception as e:
                print(f"[T1] ОШИБКА: {type(e).__name__}")


async def transaction_2_serializable():
    await asyncio.sleep(0.5)
    
    async with get_async_session() as session:
        async with session.begin():
            await set_isolation_level(session, "SERIALIZABLE")
            print("[T2] Начало транзакции (SERIALIZABLE)")
            
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            print(f"[T2] Прочитали Alice: ${account.balance}")
            
            account.balance += 50
            print(f"[T2] Обновляем баланс Alice")
            
            try:
                await session.commit()
                print("[T2] COMMIT успешен")
            except Exception as e:
                print(f"[T2] ОШИБКА: {type(e).__name__}")


async def demo_phantom_reads():
    print("\n" + "="*70)
    print("СЦЕНАРИЙ 1: REPEATABLE READ предотвращает Phantom Reads")
    print("="*70 + "\n")
    
    await init_database()
    await asyncio.gather(
        transaction_1_repeatable_read(),
        transaction_2_insert_account()
    )


async def demo_serializable():
    print("\n" + "="*70)
    print("СЦЕНАРИЙ 2: SERIALIZABLE обнаруживает конфликты")
    print("="*70 + "\n")
    
    await init_database()
    
    try:
        await asyncio.gather(
            transaction_1_serializable(),
            transaction_2_serializable()
        )
    except Exception:
        pass


async def main():
    await demo_phantom_reads()
    await asyncio.sleep(1)
    await demo_serializable()


if __name__ == "__main__":
    asyncio.run(main())
