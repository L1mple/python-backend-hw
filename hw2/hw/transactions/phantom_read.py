import asyncio
import os
import asyncpg

DB_URL = os.getenv('ASYNCPG_DATABASE_URL', 'postgresql://shop_user:shop_pass@localhost:5432/shop_db')

async def setup():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute('CREATE TABLE IF NOT EXISTS items (id serial primary key, price int)')
    await conn.execute('TRUNCATE items')
    await conn.execute('INSERT INTO items (price) VALUES (10), (20)')
    await conn.close()


async def reader(level):
    conn = await asyncpg.connect(DB_URL)
    tr = conn.transaction(isolation=level)
    await tr.start()
    cnt1 = await conn.fetchval('SELECT count(*) FROM items WHERE price > 5')
    print(f'Reader initial count (isolation={level}):', cnt1)
    # wait for writer to insert a new row and commit
    await asyncio.sleep(2)
    cnt2 = await conn.fetchval('SELECT count(*) FROM items WHERE price > 5')
    print(f'Reader second count (isolation={level}):', cnt2)
    await tr.commit()
    await conn.close()


async def writer():
    await asyncio.sleep(0.5)
    conn = await asyncpg.connect(DB_URL)
    tr = conn.transaction()
    await tr.start()
    await conn.execute('INSERT INTO items (price) VALUES (30)')
    await tr.commit()
    await conn.close()


async def main():
    await setup()
    print('--- REPEATABLE READ (phantom possible) ---')
    await asyncio.gather(reader('repeatable_read'), writer())

    await asyncio.sleep(1)

    print('\n--- SERIALIZABLE (no phantom) ---')
    await asyncio.gather(reader('serializable'), writer())


if __name__ == '__main__':
    asyncio.run(main())
