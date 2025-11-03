from http import HTTPStatus
from typing import Any, Awaitable, Callable

from helpers import send_json


async def handle_fibonacci(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    path = scope.get("path", "")
    
    path_parts = path.split("/")
    if len(path_parts) != 3:
        return await send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Invalid path format"})
    
    try:
        n = int(path_parts[2])
    except ValueError:
        return await send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Parameter must be an integer"})
    
    if n < 0:
        return await send_json(send, HTTPStatus.BAD_REQUEST, {"error": "Parameter must be non-negative"})
    
    result = calculate_fibonacci(n)
    return await send_json(send, HTTPStatus.OK, {"result": result})


def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
