import asyncio
import os
import asyncpg

DB_URL = os.getenv('ASYNCPG_DATABASE_URL', 'postgresql://shop_user:shop_pass@localhost:5432/shop_db')

async def setup():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute('CREATE TABLE IF NOT EXISTS t (id serial primary key, val int)')
    await conn.execute('TRUNCATE t')
    await conn.execute('INSERT INTO t (val) VALUES (1)')
    await conn.close()


async def reader(level):
    conn = await asyncpg.connect(DB_URL)
    tr = conn.transaction(isolation=level)
    await tr.start()
    v1 = await conn.fetchval('SELECT val FROM t WHERE id=1')
    print(f'Reader initial read (isolation={level}):', v1)
    # wait for writer to change value and commit
    await asyncio.sleep(2)
    v2 = await conn.fetchval('SELECT val FROM t WHERE id=1')
    print(f'Reader second read (isolation={level}):', v2)
    await tr.commit()
    await conn.close()


async def writer():
    await asyncio.sleep(0.5)
    conn = await asyncpg.connect(DB_URL)
    tr = conn.transaction()
    await tr.start()
    await conn.execute('UPDATE t SET val = 2 WHERE id=1')
    await tr.commit()
    await conn.close()


async def main():
    await setup()
    # Demonstrate read committed: reader sees updated value on second read
    print('--- READ COMMITTED ---')
    await asyncio.gather(reader('read_committed'), writer())

    await asyncio.sleep(1)

    # Demonstrate repeatable read: reader sees same value on second read
    print('\n--- REPEATABLE READ ---')
    await asyncio.gather(reader('repeatable_read'), writer())


if __name__ == '__main__':
    asyncio.run(main())
