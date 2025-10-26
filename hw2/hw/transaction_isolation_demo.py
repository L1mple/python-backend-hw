import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://shop_user:shop_password@localhost:5432/shop_db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def setup_test_data():
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM items WHERE name LIKE 'Test%'"))
        await session.execute(text(
            "INSERT INTO items (name, price, deleted) VALUES ('Test Item 1', 100.0, false)"
        ))
        await session.commit()
        print(" Test data created\n")


# 1. DIRTY READ


async def demo_dirty_read_uncommitted():
    print("=" * 70)
    print("1. DIRTY READ with READ UNCOMMITTED")
    print("=" * 70)
    print(" PostgreSQL не поддерживает READ UNCOMMITTED")
    print("   Автоматически использует READ COMMITTED\n")


async def demo_no_dirty_read_committed():
    print("=" * 70)
    print("2. NO DIRTY READ with READ COMMITTED")
    print("=" * 70)
    
    async def transaction1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            print("Transaction 1: Started")
            
            await session.execute(text(
                "UPDATE items SET price = 999.0 WHERE name = 'Test Item 1'"
            ))
            print("Transaction 1: Updated price to 999.0 (not committed)")
            
            await asyncio.sleep(2)  
            
            await session.rollback()
            print("Transaction 1: Rolled back")
    
    async def transaction2():
        await asyncio.sleep(1)  
        
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            print("Transaction 2: Started")
            
            result = await session.execute(text(
                "SELECT price FROM items WHERE name = 'Test Item 1'"
            ))
            price = result.scalar()
            print(f"Transaction 2: Read price = {price}")
            print("✅ Transaction 2 sees COMMITTED value (100.0), not uncommitted (999.0)")
            
            await session.commit()
    
    await asyncio.gather(transaction1(), transaction2())
    print()



# 2. NON-REPEATABLE READ

async def demo_non_repeatable_read_committed():
    """
    READ COMMITTED: Показывает Non-Repeatable Read
    """
    print("=" * 70)
    print("3. NON-REPEATABLE READ with READ COMMITTED")
    print("=" * 70)
    
    async def transaction1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL READ COMMITTED"))
            print("Transaction 1: Started")
            
            result = await session.execute(text(
                "SELECT price FROM items WHERE name = 'Test Item 1'"
            ))
            price1 = result.scalar()
            print(f"Transaction 1: First read, price = {price1}")
            
            await asyncio.sleep(2)  
            
            result = await session.execute(text(
                "SELECT price FROM items WHERE name = 'Test Item 1'"
            ))
            price2 = result.scalar()
            print(f"Transaction 1: Second read, price = {price2}")
            
            if price1 != price2:
                print("❌ NON-REPEATABLE READ detected!")
                print(f"   First read: {price1}, Second read: {price2}")
            
            await session.commit()
    
    async def transaction2():
        await asyncio.sleep(1) 
        
        async with async_session_maker() as session:
            print("Transaction 2: Started")
            
            await session.execute(text(
                "UPDATE items SET price = 200.0 WHERE name = 'Test Item 1'"
            ))
            print("Transaction 2: Updated price to 200.0")
            
            await session.commit()
            print("Transaction 2: Committed")
    
    await asyncio.gather(transaction1(), transaction2())
    
 
    async with async_session_maker() as session:
        await session.execute(text(
            "UPDATE items SET price = 100.0 WHERE name = 'Test Item 1'"
        ))
        await session.commit()
    print()


async def demo_no_non_repeatable_read_repeatable():
    """
    REPEATABLE READ: Нет Non-Repeatable Read
    """
    print("=" * 70)
    print("4. NO NON-REPEATABLE READ with REPEATABLE READ")
    print("=" * 70)
    
    async def transaction1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            print("Transaction 1: Started with REPEATABLE READ")
            
      
            result = await session.execute(text(
                "SELECT price FROM items WHERE name = 'Test Item 1'"
            ))
            price1 = result.scalar()
            print(f"Transaction 1: First read, price = {price1}")
            
            await asyncio.sleep(2)  
            
           
            result = await session.execute(text(
                "SELECT price FROM items WHERE name = 'Test Item 1'"
            ))
            price2 = result.scalar()
            print(f"Transaction 1: Second read, price = {price2}")
            
            if price1 == price2:
                print("✅ NO NON-REPEATABLE READ!")
                print(f"   Both reads return: {price1}")
            
            await session.commit()
    
    async def transaction2():
        await asyncio.sleep(1)
        
        async with async_session_maker() as session:
            print("Transaction 2: Started")
            
            await session.execute(text(
                "UPDATE items SET price = 300.0 WHERE name = 'Test Item 1'"
            ))
            print("Transaction 2: Updated price to 300.0")
            
            await session.commit()
            print("Transaction 2: Committed")
    
    await asyncio.gather(transaction1(), transaction2())
    

    async with async_session_maker() as session:
        await session.execute(text(
            "UPDATE items SET price = 100.0 WHERE name = 'Test Item 1'"
        ))
        await session.commit()
    print()



# 3. PHANTOM READ


async def demo_phantom_read_repeatable():
    """
    REPEATABLE READ: Показывает Phantom Read
    """
    print("=" * 70)
    print("5. PHANTOM READ with REPEATABLE READ")
    print("=" * 70)
    
    async def transaction1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ"))
            print("Transaction 1: Started with REPEATABLE READ")
            
            result = await session.execute(text(
                "SELECT COUNT(*) FROM items WHERE name LIKE 'Test%'"
            ))
            count1 = result.scalar()
            print(f"Transaction 1: First count = {count1}")
            
            await asyncio.sleep(2) 
            
            result = await session.execute(text(
                "SELECT COUNT(*) FROM items WHERE name LIKE 'Test%'"
            ))
            count2 = result.scalar()
            print(f"Transaction 1: Second count = {count2}")
            
            if count1 == count2:
                print("✅ NO PHANTOM READ in PostgreSQL!")
                print("   PostgreSQL's REPEATABLE READ предотвращает Phantom Reads")
            else:
                print("❌ PHANTOM READ detected!")
            
            await session.commit()
    
    async def transaction2():
        await asyncio.sleep(1)
        
        async with async_session_maker() as session:
            print("Transaction 2: Started")
            
            await session.execute(text(
                "INSERT INTO items (name, price, deleted) VALUES ('Test Item 2', 150.0, false)"
            ))
            print("Transaction 2: Inserted new item")
            
            await session.commit()
            print("Transaction 2: Committed")
    
    await asyncio.gather(transaction1(), transaction2())
    
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM items WHERE name = 'Test Item 2'"))
        await session.commit()
    print()


async def demo_no_phantom_read_serializable():
    """
    SERIALIZABLE: Нет Phantom Read
    """
    print("=" * 70)
    print("6. NO PHANTOM READ with SERIALIZABLE")
    print("=" * 70)
    
    async def transaction1():
        async with async_session_maker() as session:
            await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
            print("Transaction 1: Started with SERIALIZABLE")
            
            result = await session.execute(text(
                "SELECT COUNT(*) FROM items WHERE name LIKE 'Test%'"
            ))
            count1 = result.scalar()
            print(f"Transaction 1: First count = {count1}")
            
            await asyncio.sleep(2)
            
            result = await session.execute(text(
                "SELECT COUNT(*) FROM items WHERE name LIKE 'Test%'"
            ))
            count2 = result.scalar()
            print(f"Transaction 1: Second count = {count2}")
            
            if count1 == count2:
                print("✅ NO PHANTOM READ with SERIALIZABLE!")
            
            await session.commit()
            print("Transaction 1: Committed")
    
    async def transaction2():
        await asyncio.sleep(1)
        
        try:
            async with async_session_maker() as session:
                await session.execute(text("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE"))
                print("Transaction 2: Started with SERIALIZABLE")
                
                await session.execute(text(
                    "INSERT INTO items (name, price, deleted) VALUES ('Test Item 3', 150.0, false)"
                ))
                print("Transaction 2: Trying to insert new item...")
                
                await session.commit()
                print("Transaction 2: Committed")
        except Exception as e:
            print(f"Transaction 2: ❌ Serialization conflict! {e}")
            print("   PostgreSQL предотвратил конфликт сериализации")
    
    await asyncio.gather(transaction1(), transaction2())
    
    async with async_session_maker() as session:
        await session.execute(text("DELETE FROM items WHERE name = 'Test Item 3'"))
        await session.commit()
    print()


async def main():
    print("\n" + "=" * 70)
    print("=" * 70 + "\n")
    
    await setup_test_data()
    
    await demo_dirty_read_uncommitted()
    await demo_no_dirty_read_committed()
    await demo_non_repeatable_read_committed()
    await demo_no_non_repeatable_read_repeatable()
    await demo_phantom_read_repeatable()
    await demo_no_phantom_read_serializable()
    
    print("=" * 70)
    print("РЕЗЮМЕ:")
    print("=" * 70)
    print(" READ COMMITTED: Предотвращает Dirty Reads")
    print(" REPEATABLE READ: Предотвращает Dirty + Non-Repeatable Reads")
    print("   (В PostgreSQL также предотвращает Phantom Reads!)")
    print(" SERIALIZABLE: Полная изоляция, конфликты сериализации")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    asyncio.run(main())