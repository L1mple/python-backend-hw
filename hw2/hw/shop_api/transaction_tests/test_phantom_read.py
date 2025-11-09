import asyncio
from sqlalchemy import text
from .utils import engine, setup

SELECT_SQL = "SELECT id, name FROM test_items WHERE name LIKE 'p%' ORDER BY id;"
INSERT_SQL = "INSERT INTO test_items (id, name) VALUES (2, 'paper');"

async def _reader(level: str):
    async with engine.connect() as conn:
        await conn.execute(text(f"BEGIN ISOLATION LEVEL {level}"))
        rows1 = (await conn.execute(text(SELECT_SQL))).fetchall()
        print(f"T1[{level}] SELECT #1 -> {rows1}")
        await asyncio.sleep(2)  # ждём, пока T2 вставит строку
        rows2 = (await conn.execute(text(SELECT_SQL))).fetchall()
        print(f"T1[{level}] SELECT #2 -> {rows2}")
        await conn.execute(text("COMMIT"))

async def _writer():
    async with engine.connect() as conn:
        await asyncio.sleep(1)
        await conn.execute(text("BEGIN"))
        await conn.execute(text(INSERT_SQL))
        await conn.execute(text("COMMIT"))
        print("T2: INSERT (2, 'paper') + COMMIT")

async def run():
    # READ COMMITTED → фантом возможен
    await setup()
    print("\n--- PHANTOM READ on READ COMMITTED ---")
    await asyncio.gather(_reader("READ COMMITTED"), _writer())

    # REPEATABLE READ → фантома нет
    await setup()
    print("\n--- NO PHANTOM on REPEATABLE READ ---")
    await asyncio.gather(_reader("REPEATABLE READ"), _writer())

    # финальная проверка (вне транзакций)
    async with engine.connect() as conn:
        final = (await conn.execute(text(SELECT_SQL))).fetchall()
        print(f"FINAL outside: {final}")
