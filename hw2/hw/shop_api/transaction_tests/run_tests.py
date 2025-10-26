import asyncio

async def main():
    print("\n=== DIRTY READ: READ UNCOMMITTED vs READ COMMITTED (PostgreSQL: одинаково) ===")
    from .test_dirty_read import run as run_dirty
    await run_dirty()

    print("\n=== NON-REPEATABLE READ (READ COMMITTED) ===")
    from .test_non_repeatable_read import run as run_nonrep
    await run_nonrep()

    print("\n=== REPEATABLE READ (нет non-repeatable) ===")
    from .test_repeatable_read import run as run_rr
    await run_rr()

    print("\n=== PHANTOM READ (READ COMMITTED vs REPEATABLE READ: PostgreSQL: нет phantom в REPEATABLE READ) ===")
    from .test_phantom_read import run as run_phantom
    await run_phantom()

if __name__ == "__main__":
    asyncio.run(main())

