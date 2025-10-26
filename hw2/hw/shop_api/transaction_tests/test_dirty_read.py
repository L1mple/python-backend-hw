import asyncio
from sqlalchemy import text
from .utils import engine, setup, SELECT_ONE, UPDATE_TO_PENCIL

async def _writer_hold_then_rollback():
    # T1: UPDATE без коммита, затем ROLLBACK
    async with engine.connect() as conn:
        await conn.execute(text("BEGIN"))
        await conn.execute(text(UPDATE_TO_PENCIL))
        print("T1: UPDATE name='pencil' (не закоммичено)")
        await asyncio.sleep(2)
        await conn.execute(text("ROLLBACK"))
        print("T1: ROLLBACK")

async def _reader_select(level: str, tag: str):
    # T2: чтение под заданным уровнем
    async with engine.connect() as conn:
        await conn.execute(text(f"BEGIN ISOLATION LEVEL {level}"))
        rows = (await conn.execute(text(SELECT_ONE))).fetchall()
        print(f"{tag}: SELECT * -> {rows}")
        await conn.execute(text("COMMIT"))

async def run():
    await setup()
    t_writer = asyncio.create_task(_writer_hold_then_rollback())
    await asyncio.sleep(1)  # дать писателю обновить и удерживать
    await _reader_select("READ UNCOMMITTED", "T2 (RU)")   # в PG это будет как RC
    await _reader_select("READ COMMITTED",   "T2 (RC)")
    await t_writer
    # финальная проверка
    async with engine.connect() as conn:
        rows = (await conn.execute(text(SELECT_ONE))).fetchall()
        print(f"FINAL: SELECT * -> {rows}")
