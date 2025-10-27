from typing import Any, Awaitable, Callable
import math
import json
from urllib.parse import parse_qs
from http import HTTPStatus


def compute_fibonacci(n: int) -> int:
    if n == 0:
        return 0
    a, b = 0, 1
    for _ in range(1, n + 1):
        a, b = b, a + b
    return a


async def send_response(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    body: bytes = b"",
    content_type: bytes = b"text/plain",
):
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [[b"content-type", content_type]],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def send_json(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    data: dict[str, Any],
    status: int = HTTPStatus.OK,
):
    body = json.dumps(data).encode("utf-8")
    await send_response(send, status, body, b"application/json")


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
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    elif scope["type"] == "http":
        method = scope["method"]
        path = scope["path"]

        if path == "/factorial":
            if method != "GET":
                await send_response(send, HTTPStatus.METHOD_NOT_ALLOWED, b"Method Not Allowed")
                return
            query_string = scope["query_string"].decode()
            query = parse_qs(query_string)
            n_str = query.get("n", [None])[0]
            if n_str is None:
                await send_response(send, HTTPStatus.UNPROCESSABLE_ENTITY, b"Missing parameter 'n'")
                return
            try:
                n = int(n_str)
            except ValueError:
                await send_response(send, HTTPStatus.UNPROCESSABLE_ENTITY, b"Invalid parameter 'n'")
                return
            if n < 0:
                await send_response(send, HTTPStatus.BAD_REQUEST, b"Parameter 'n' must be non-negative")
                return
            result = math.factorial(n)
            await send_json(send, {"result": result})

        elif path.startswith("/fibonacci/"):
            if method != "GET":
                await send_response(send, HTTPStatus.METHOD_NOT_ALLOWED, b"Method Not Allowed")
                return
            n_str = path[len("/fibonacci/"):]
            if not n_str:
                await send_response(send, HTTPStatus.UNPROCESSABLE_ENTITY, b"Missing number in path")
                return
            try:
                n = int(n_str)
            except ValueError:
                await send_response(send, HTTPStatus.UNPROCESSABLE_ENTITY, b"Invalid number in path")
                return
            if n < 0:
                await send_response(send, HTTPStatus.BAD_REQUEST, b"Number must be non-negative")
                return
            result = compute_fibonacci(n)
            await send_json(send, {"result": result})

        elif path == "/mean":
            if method != "GET":
                await send_response(send, HTTPStatus.METHOD_NOT_ALLOWED, b"Method Not Allowed")
                return
            message = await receive()
            if message["type"] != "http.request":
                await send_response(send, HTTPStatus.INTERNAL_SERVER_ERROR, b"Invalid request")
                return
            body = message.get("body", b"")
            if not body:
                await send_response(send, HTTPStatus.UNPROCESSABLE_ENTITY, b"Empty body")
                return
            try:
                data = json.loads(body)
                if not isinstance(data, list):
                    await send_response(send, HTTPStatus.UNPROCESSABLE_ENTITY, b"Body must be a list")
                    return
                if not data:
                    await send_response(send, HTTPStatus.BAD_REQUEST, b"Empty list")
                    return
                numbers = []
                for item in data:
                    if not isinstance(item, (int, float)):
                        await send_response(send, HTTPStatus.UNPROCESSABLE_ENTITY, b"All elements must be numbers")
                        return
                    numbers.append(float(item))
                mean_value = sum(numbers) / len(numbers)
                await send_json(send, {"result": mean_value})
            except json.JSONDecodeError:
                await send_response(send, HTTPStatus.UNPROCESSABLE_ENTITY, b"Invalid JSON")
                return
        else:
            await send_response(send, HTTPStatus.NOT_FOUND, b"Not Found")
    else:
        return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000)
