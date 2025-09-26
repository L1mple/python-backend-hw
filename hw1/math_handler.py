from http import HTTPStatus
import json
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs

from utils import send_response

def factorial(n: int) -> int:
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


async def handle_factorial(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
): 
    query = {k: v[0] for k, v in parse_qs(scope["query_string"].decode()).items()}

    print(query)

    if "n" not in query:
        await send_response({"error": "Missing query parameter 'n'"}, send, HTTPStatus.UNPROCESSABLE_ENTITY)
        return
    if query["n"].startswith("-"):
        await send_response({"error": "Query parameter 'n' must be a non-negative integer"}, send, HTTPStatus.BAD_REQUEST)
        return
    if not query["n"].isdigit():
        await send_response({"error": "Query parameter 'n' must be an integer"}, send, HTTPStatus.UNPROCESSABLE_ENTITY)
        return
    n = int(query["n"])

    await send_response({"result": factorial(n)}, send)


def fibonacci(n: int) -> int:
    if n == 0:
        return 0
    elif n == 1:
        return 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b


async def handle_fibonacci(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
): 
    path = scope["path"].strip("/").split("/")
    if len(path) != 2:
        await send_response({"error": "Invalid path"}, send, HTTPStatus.UNPROCESSABLE_ENTITY)
        return
    if path[1].startswith("-"):
        await send_response({"error": "Path parameter must be a non-negative integer"}, send, HTTPStatus.BAD_REQUEST)
        return
    if not path[1].isdigit():
        await send_response({"error": "Path parameter must be an integer"}, send, HTTPStatus.UNPROCESSABLE_ENTITY)
        return
    n = int(path[1])
    

    await send_response({"result": fibonacci(n)}, send)


def mean(numbers: list[float]) -> float:
    if not numbers:
        return 0.0
    return sum(numbers) / len(numbers)


async def handle_mean(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    try:
        numbers = json.loads(body)
        if not isinstance(numbers, list) or not all(isinstance(x, (int, float)) for x in numbers):
            raise ValueError
    except (json.JSONDecodeError, ValueError):
        await send_response({"error": "Request body must be a JSON array of numbers"}, send, HTTPStatus.UNPROCESSABLE_ENTITY)
        return

    if not numbers:
        await send_response({"error": "Array must not be empty"}, send, HTTPStatus.BAD_REQUEST)
        return

    await send_response({"result": mean(numbers)}, send)