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


async def reader():
    conn = await asyncpg.connect(DB_URL)
    tr = conn.transaction(isolation='read_committed')
    await tr.start()
    v1 = await conn.fetchval('SELECT val FROM t WHERE id=1')
    print('Reader initial read:', v1)
    await asyncio.sleep(2)
    v2 = await conn.fetchval('SELECT val FROM t WHERE id=1')
    print('Reader second read:', v2)
    await tr.commit()
    await conn.close()


async def writer():
    await asyncio.sleep(0.5)
    conn = await asyncpg.connect(DB_URL)
    tr = conn.transaction()
    await tr.start()
    await conn.execute('UPDATE t SET val = 2 WHERE id=1')
    await asyncio.sleep(2)
    await tr.rollback()
    await conn.close()


async def main():
    await setup()
    print('--- Attempt dirty read demonstration (Postgres prevents dirty reads) ---')
    await asyncio.gather(reader(), writer())


if __name__ == '__main__':
    asyncio.run(main())
