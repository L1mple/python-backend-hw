from typing import Any, Awaitable, Callable
from http import HTTPStatus
from typing import List
import math, json


def fibonacci(n: int) -> int:
    if n in (0, 1):
        return n
    a, b = 0, 1
    for _ in range(2, n):
        a, b = b, a + b
    return b


async def parse_endpoint(
    scope, receive: Callable[[], Awaitable[dict[str, Any]]], status=200
):
    path = scope.get("path", None)
    if not path:
        return 404, None

    query_string = scope.get("query_string", b"")

    if path.startswith("/fibonacci/"):
        try:
            n = int(path.split("/fibonacci/")[1])
            if n < 0:
                return 400, None
            return status, fibonacci(n)
        except (IndexError, ValueError):
            return 422, None

    elif path == "/factorial":
        query_string = query_string.decode("utf-8")
        try:
            n = int(query_string.split("n=")[1])
            if n < 0:
                return 400, None
            return status, math.factorial(n)
        except (IndexError, ValueError):
            return 422, None

    elif path == "/mean":

        query_string = query_string.decode("utf-8")
        event = await receive()
        event = event.get("body", b"")

        event = json.loads(event.decode())

        if event is None:
            return 422, None
        if len(event) == 0:
            return 400, None
        try:
            numbers = event
            numbers = sum(numbers) / len(numbers)
            return status, numbers
        except (IndexError, ValueError):
            return 422, None

    return 404, None


async def processor(
    scope,
    send,
    receive: Callable[[], Awaitable[dict[str, Any]]],
):
    status, res = await parse_endpoint(scope, receive)

    if res is None:
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [[b"content-type", b"application/json"]],
            }
        )
        return await send({"type": "http.response.body", "body": b"Not found"})

    res = {"result": f"{res}"}
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        }
    )
    return await send({"type": "http.response.body", "body": json.dumps(res).encode()})


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    """
    Args:
        scope: Словарь с информацией о запросе
        receive: Корутина для получения сообщений от клиента
        send: Корутина для отправки сообщений клиенту
    """
    # assert scope["type"] == "http"
    await processor(scope, send, receive)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
