from http import HTTPStatus
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs

from helpers import send_json


async def handle_factorial(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    query_string = scope.get("query_string", b"").decode("utf-8")
    query_params = parse_qs(query_string)
    
    if "n" not in query_params:
        return await send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Missing parameter 'n'"})
    
    try:
        n = int(query_params["n"][0])
    except (ValueError, IndexError):
        return await send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Parameter 'n' must be an integer"})
    
    if n < 0:
        return await send_json(send, HTTPStatus.BAD_REQUEST, {"error": "Parameter 'n' must be non-negative"})
    
    result = calculate_factorial(n)
    return await send_json(send, HTTPStatus.OK, {"result": result})

def calculate_factorial(n: int) -> int:
    if n == 0:
        return 1
    
    res = 1
    for i in range(1, n + 1):
        res *= i
    return res
