"""
ДЕМОНСТРАЦИЯ: Non-Repeatable Read (Неповторяющееся чтение)

Non-Repeatable Read возникает когда транзакция читает одни и те же данные дважды,
но между чтениями другая транзакция изменяет и коммитит эти данные.

Проблема: один и тот же SELECT в рамках транзакции возвращает разные результаты.

Уровни изоляции:
- READ COMMITTED: допускает Non-Repeatable Read
- REPEATABLE READ: предотвращает Non-Repeatable Read
"""
import asyncio
from sqlalchemy import select
from db_setup import Account, get_async_session, init_database, set_isolation_level


async def transaction_1_read_committed():
    async with get_async_session() as session:
        async with session.begin():
            await set_isolation_level(session, "READ COMMITTED")
            print("[T1] Начало транзакции (READ COMMITTED)")
            
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            balance_1 = account.balance
            print(f"[T1] Первое чтение: Alice = ${balance_1}")
            
            await asyncio.sleep(1)
            
            session.expire_all()
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            balance_2 = account.balance
            print(f"[T1] Второе чтение: Alice = ${balance_2}")
            
            if balance_1 != balance_2:
                print(f"[T1] NON-REPEATABLE READ: значение изменилось")


async def transaction_2_modify_and_commit():
    await asyncio.sleep(0.5)
    
    async with get_async_session() as session:
        async with session.begin():
            print("[T2] Начало транзакции")
            
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            old_balance = account.balance
            account.balance = old_balance + 500
            
            print(f"[T2] Изменили баланс: ${old_balance} -> ${account.balance}")
            await session.commit()
            print("[T2] COMMIT")


async def transaction_1_repeatable_read():
    async with get_async_session() as session:
        async with session.begin():
            await set_isolation_level(session, "REPEATABLE READ")
            print("[T1] Начало транзакции (REPEATABLE READ)")
            
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            balance_1 = account.balance
            print(f"[T1] Первое чтение: Alice = ${balance_1}")
            
            await asyncio.sleep(1)
            
            session.expire_all()
            result = await session.execute(select(Account).where(Account.id == 1))
            account = result.scalar_one()
            balance_2 = account.balance
            print(f"[T1] Второе чтение: Alice = ${balance_2}")
            
            if balance_1 == balance_2:
                print("[T1] REPEATABLE READ работает: данные не изменились")


async def demo_non_repeatable_read():
    print("\n" + "="*70)
    print("СЦЕНАРИЙ 1: READ COMMITTED допускает Non-Repeatable Read")
    print("="*70 + "\n")
    
    await init_database()
    await asyncio.gather(
        transaction_1_read_committed(),
        transaction_2_modify_and_commit()
    )


async def demo_repeatable_read():
    print("\n" + "="*70)
    print("СЦЕНАРИЙ 2: REPEATABLE READ предотвращает Non-Repeatable Read")
    print("="*70 + "\n")
    
    await init_database()
    await asyncio.gather(
        transaction_1_repeatable_read(),
        transaction_2_modify_and_commit()
    )


async def main():
    await demo_non_repeatable_read()
    await asyncio.sleep(1)
    await demo_repeatable_read()


if __name__ == "__main__":
    asyncio.run(main())
