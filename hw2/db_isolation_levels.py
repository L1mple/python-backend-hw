import asyncio
import asyncpg
from hw.shop_api import SCHEMA_SQL


async def get_sample_connections(connection_str: str):
    connection_1 = await asyncpg.connect(connection_str)
    connection_2 = await asyncpg.connect(connection_str)
    return connection_1, connection_2


async def initialize_test_database(connection: asyncpg.Connection, sql_script: str):
    await connection.execute(sql_script)


async def table_exists(connection: asyncpg.Connection, table_name: str) -> bool:
    query = """
    SELECT EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = $1
    )
    """
    return await connection.fetchval(query, table_name)


async def ensure_schema_exists(connection: asyncpg.Connection, sql_script: str):
    tables = ["item", "cart", "cart_item"]
    existing = [await table_exists(connection, t) for t in tables]
    if not all(existing):
        await initialize_test_database(connection, sql_script)


async def reset_test_rows(connection: asyncpg.Connection, names: list[str]):
    for name in names:
        await connection.execute("DELETE FROM item WHERE name = $1", name)


async def test_dirty_read(connection_1: asyncpg.Connection, connection_2: asyncpg.Connection):
    await reset_test_rows(connection_1, ["item_1", "item_2"])
    await connection_1.execute("INSERT INTO item (name, price) VALUES ('item_1', 100), ('item_2', 200)")

    await connection_1.execute("BEGIN ISOLATION LEVEL READ UNCOMMITTED")
    await connection_1.execute("UPDATE item SET price = 300 WHERE name = 'item_1'")

    price = await connection_2.fetchval("SELECT price FROM item WHERE name = 'item_1'")
    assert price == 100, "Dirty read should not see uncommitted changes"

    await connection_1.execute("ROLLBACK")
    price_after = await connection_2.fetchval("SELECT price FROM item WHERE name = 'item_1'")
    assert price_after == 100, "Price should revert after rollback"


async def test_non_repeatable_read(connection_1: asyncpg.Connection, connection_2: asyncpg.Connection):
    await reset_test_rows(connection_1, ["item_nr"])
    await connection_1.execute("INSERT INTO item (name, price) VALUES ('item_nr', 500)")

    await connection_1.execute("BEGIN ISOLATION LEVEL READ COMMITTED")
    price1 = await connection_1.fetchval("SELECT price FROM item WHERE name = 'item_nr'")
    print(f"Transaction 1 - First read: {price1}")

    await connection_2.execute("BEGIN")
    await connection_2.execute("UPDATE item SET price = 700 WHERE name = 'item_nr'")
    await connection_2.execute("COMMIT")

    price2 = await connection_1.fetchval("SELECT price FROM item WHERE name = 'item_nr'")
    print(f"Transaction 1 - Second read: {price2}")

    assert price1 != price2, "Non-repeatable read should detect changed value"
    await connection_1.execute("COMMIT")


async def test_non_repeatable_read_repeatable(connection_1: asyncpg.Connection, connection_2: asyncpg.Connection):
    await reset_test_rows(connection_1, ["item_nr"])
    await connection_1.execute("INSERT INTO item (name, price) VALUES ('item_nr', 800)")

    await connection_1.execute("BEGIN ISOLATION LEVEL REPEATABLE READ")
    price1 = await connection_1.fetchval("SELECT price FROM item WHERE name = 'item_nr'")
    print(f"Transaction 1 (repeatable) - First read: {price1}")

    await connection_2.execute("BEGIN")
    await connection_2.execute("UPDATE item SET price = 900 WHERE name = 'item_nr'")
    await connection_2.execute("COMMIT")

    price2 = await connection_1.fetchval("SELECT price FROM item WHERE name = 'item_nr'")
    print(f"Transaction 1 (repeatable) - Second read: {price2}")

    assert price1 == price2, "Repeatable read prevents non-repeatable reads"
    await connection_1.execute("COMMIT")


async def test_phantom_read(connection_1: asyncpg.Connection, connection_2: asyncpg.Connection):
    await reset_test_rows(connection_1, ["phantom_1", "phantom_2"])
    await connection_1.execute("BEGIN ISOLATION LEVEL READ COMMITTED")

    count1 = await connection_1.fetchval("SELECT COUNT(*) FROM item WHERE name LIKE 'phantom_%'")
    print(f"Transaction 1 - Initial count: {count1}")

    await connection_2.execute("BEGIN")
    await connection_2.execute("INSERT INTO item (name, price) VALUES ('phantom_1', 123)")
    await connection_2.execute("COMMIT")

    count2 = await connection_1.fetchval("SELECT COUNT(*) FROM item WHERE name LIKE 'phantom_%'")
    print(f"Transaction 1 - Count after second read: {count2}")

    assert count2 > count1, "Phantom read should detect new row appearing"
    await connection_1.execute("COMMIT")


async def test_phantom_read_serializable(connection_1: asyncpg.Connection, connection_2: asyncpg.Connection):
    await reset_test_rows(connection_1, ["phantom_1", "phantom_2"])
    await connection_1.execute("BEGIN ISOLATION LEVEL SERIALIZABLE")

    count1 = await connection_1.fetchval("SELECT COUNT(*) FROM item WHERE name LIKE 'phantom_%'")
    print(f"Transaction 1 (serializable) - Initial count: {count1}")

    try:
        await connection_2.execute("BEGIN ISOLATION LEVEL SERIALIZABLE")
        await connection_2.execute("INSERT INTO item (name, price) VALUES ('phantom_2', 456)")
        await connection_2.execute("COMMIT")
    except asyncpg.SerializationError:
        print("Transaction 2 failed due to serialization conflict")

    count2 = await connection_1.fetchval("SELECT COUNT(*) FROM item WHERE name LIKE 'phantom_%'")
    print(f"Transaction 1 (serializable) - Count after second read: {count2}")

    assert count1 == count2, "Serializable prevents phantom reads"
    await connection_1.execute("COMMIT")


async def main():
    conn_str = "postgresql://postgres:postgres@localhost:5432/shop"
    conn_1, conn_2 = await get_sample_connections(conn_str)

    try:
        await ensure_schema_exists(conn_1, SCHEMA_SQL)

        print("Running dirty read test")
        await test_dirty_read(conn_1, conn_2)

        print("Running non-repeatable read test")
        await test_non_repeatable_read(conn_1, conn_2)

        print("Running repeatable read test")
        await test_non_repeatable_read_repeatable(conn_1, conn_2)

        print("Running phantom read test")
        await test_phantom_read(conn_1, conn_2)

        print("Running serializable phantom read test")
        await test_phantom_read_serializable(conn_1, conn_2)

        print("All tests completed successfully")
    except AssertionError as e:
        print("Assertion failed:", e)
        raise
    finally:
        await conn_1.close()
        await conn_2.close()


if __name__ == '__main__':
    asyncio.run(main())
