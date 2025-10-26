import asyncio
from sqlalchemy import text
from .utils import engine, setup, SELECT_ONE, UPDATE_TO_PENCIL

async def _reader_rc_two_selects():
    # T1: в одной транзакции RC дважды читает одну строку
    async with engine.connect() as conn:
        await conn.execute(text("BEGIN ISOLATION LEVEL READ COMMITTED"))
        rows1 = (await conn.execute(text(SELECT_ONE))).fetchall()
        print(f"T1: SELECT #1 -> {rows1}")
        await asyncio.sleep(1)  # ждём, пока писатель закоммитит изменение
        rows2 = (await conn.execute(text(SELECT_ONE))).fetchall()
        print(f"T1: SELECT #2 -> {rows2}")
        await conn.execute(text("COMMIT"))

async def _writer_commit_update():
    # T2: обновляет и коммитит между двумя SELECT T1
    async with engine.connect() as conn:
        await asyncio.sleep(0.5)  # чтобы SELECT #1 уже выполнился
        await conn.execute(text("BEGIN"))
        await conn.execute(text(UPDATE_TO_PENCIL))
        await conn.execute(text("COMMIT"))
        print("T2: UPDATE name='pencil' и COMMIT")

async def run():
    await setup()
    await asyncio.gather(
        _reader_rc_two_selects(),
        _writer_commit_update(),
    )
    # итог
    async with engine.connect() as conn:
        rows = (await conn.execute(text(SELECT_ONE))).fetchall()
        print(f"FINAL: SELECT * -> {rows}")
