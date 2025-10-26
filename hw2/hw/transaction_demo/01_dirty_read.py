"""
ДЕМОНСТРАЦИЯ: Dirty Read (Грязное чтение)

Dirty Read возникает когда транзакция читает данные, которые были изменены
другой транзакцией, но еще не закоммичены (uncommitted).

Проблема: если вторая транзакция откатится (ROLLBACK), первая транзакция
прочитала "несуществующие" данные.

Уровни изоляции:
- READ UNCOMMITTED: допускает Dirty Read
- READ COMMITTED: предотвращает Dirty Read (минимальный уровень в PostgreSQL)

ВАЖНО: PostgreSQL НЕ ПОДДЕРЖИВАЕТ READ UNCOMMITTED!
Даже если вы установите READ UNCOMMITTED, PostgreSQL использует READ COMMITTED.
Мы продемонстрируем это поведение.
"""
import asyncio
from sqlalchemy import select
from db_setup import Account, get_async_session, init_database, set_isolation_level


async def transaction_1_read_uncommitted():
    async with get_async_session() as session:
        async with session.begin():
            await set_isolation_level(session, "READ UNCOMMITTED")
            print("[T1] Начало транзакции (READ UNCOMMITTED)")
            await asyncio.sleep(0.5)
            
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            print(f"[T1] Баланс Alice: ${account.balance}")
            print("[T1] PostgreSQL использует READ COMMITTED вместо READ UNCOMMITTED")


async def transaction_2_modify_and_rollback():
    async with get_async_session() as session:
        async with session.begin():
            print("[T2] Начало транзакции")
            
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            old_balance = account.balance
            account.balance = 9999.99
            
            print(f"[T2] Изменили баланс: ${old_balance} -> ${account.balance} (не закоммичено)")
            await asyncio.sleep(1)
            
            await session.rollback()
            print("[T2] ROLLBACK")


async def transaction_1_read_committed():
    async with get_async_session() as session:
        async with session.begin():
            await set_isolation_level(session, "READ COMMITTED")
            print("[T1] Начало транзакции (READ COMMITTED)")
            await asyncio.sleep(0.5)
            
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            print(f"[T1] Баланс Alice: ${account.balance}")
            print("[T1] READ COMMITTED предотвращает Dirty Read")


async def demo_dirty_read_attempt():
    print("\n" + "="*70)
    print("СЦЕНАРИЙ 1: READ UNCOMMITTED (PostgreSQL не поддерживает)")
    print("="*70 + "\n")
    
    await init_database()
    await asyncio.gather(
        transaction_2_modify_and_rollback(),
        transaction_1_read_uncommitted()
    )


async def demo_read_committed():
    print("\n" + "="*70)
    print("СЦЕНАРИЙ 2: READ COMMITTED предотвращает Dirty Read")
    print("="*70 + "\n")
    
    await asyncio.gather(
        transaction_2_modify_and_rollback(),
        transaction_1_read_committed()
    )


async def main():
    await demo_dirty_read_attempt()
    await asyncio.sleep(1)
    await demo_read_committed()


if __name__ == "__main__":
    asyncio.run(main())
