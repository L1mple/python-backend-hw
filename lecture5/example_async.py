import asyncio
from typing import Awaitable, Callable, Iterable


async def map_async[_TVal, _TRes](
    func: Callable[[_TVal], Awaitable[_TRes]],
    values: Iterable[_TVal],
) -> Iterable[_TRes]:
    return await asyncio.gather(*(func(value) for value in values))


async def slow_map_async[_TVal, _TRes](
    func: Callable[[_TVal], Awaitable[_TRes]],
    values: Iterable[_TVal],
) -> Iterable[_TRes]:
    result = []

    for value in values:
        result.append(await func(value))
        await asyncio.sleep(0.1)

    return result
