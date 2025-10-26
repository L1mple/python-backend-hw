import asyncio
from sqlalchemy import text
from .utils import engine, setup, SELECT_ONE, UPDATE_TO_PENCIL


async def _rr_reader_same_row():
    async with engine.connect() as conn:
        await conn.execute(text("BEGIN ISOLATION LEVEL REPEATABLE READ"))
        rows1 = (await conn.execute(text(SELECT_ONE))).fetchall()
        print(f"T1[RR] SELECT #1 (by id): {rows1}")
        await asyncio.sleep(2)           # время на UPDATE другой транзакции
        rows2 = (await conn.execute(text(SELECT_ONE))).fetchall()
        print(f"T1[RR] SELECT #2 (by id): {rows2}")
        await conn.execute(text("COMMIT"))


async def _writer_update():
    async with engine.connect() as conn:
        await asyncio.sleep(1)
        await conn.execute(text("BEGIN"))
        await conn.execute(text(UPDATE_TO_PENCIL))   # pen -> pencil
        await conn.execute(text("COMMIT"))


async def test_rr_no_non_repeatable_read():
    await setup()  # [(1,'pen')]
    await asyncio.gather(
        _rr_reader_same_row(),
        _writer_update(),
    )
    # Снаружи транзакции T1 изменение уже видно:
    async with engine.connect() as conn:
        final = (await conn.execute(text(SELECT_ONE))).fetchall()
        print(f"FINAL outside (by id): {final}")


async def run():
    print("\n--- REPEATABLE READ: no non-repeatable read ---")
    await test_rr_no_non_repeatable_read()

