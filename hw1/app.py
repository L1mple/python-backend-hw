from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import json
from http import HTTPStatus


class NegativeParameterError(Exception):
    pass


def b_to_queries(scope: dict[str, Any]) -> dict[str, str]:
    raw = scope["query_string"].decode()
    return {k: v[0] for k, v in parse_qs(raw).items()}


def parse_numbers(raw: str | None) -> list[float]:
    if not raw:
        raise ValueError("missing 'numbers' param")
    try:
        return [float(x) for x in raw.split(",")]
    except ValueError:
        raise ValueError("all values must be numbers")


async def _send_json(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    payload: dict[str, Any],
):
    body = json.dumps(payload).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def factorial_handler(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    params = b_to_queries(scope)
    raw_n = params.get("n")

    if raw_n is None:
        return await _send_json(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "missing 'n' param"}
        )
    try:
        n = int(raw_n)
        result = factorial(n)
    except ValueError:
        return await _send_json(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "param must be integer"}
        )
    except NegativeParameterError as e:
        return await _send_json(send, HTTPStatus.BAD_REQUEST, {"error": str(e)})

    return await _send_json(send, HTTPStatus.OK, {"result": result})


def factorial(n: int) -> int:
    if n < 0:
        raise NegativeParameterError("n must be >= 0")
    res = 1
    for i in range(2, n + 1):
        res *= i
    return res


async def fibonacci_handler(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    parts = scope["path"].strip("/").split("/")
    raw_n = parts[1] if len(parts) > 1 else None
    if raw_n is None:
        return await _send_json(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "missing param in path"}
        )

    try:
        n = int(raw_n)
        result = fibonacci(n)
    except NegativeParameterError:
        return await _send_json(
            send, HTTPStatus.BAD_REQUEST, {"error": "param must be integer"}
        )
    except ValueError as e:
        return await _send_json(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": str(e)}
        )

    return await _send_json(send, HTTPStatus.OK, {"result": result})


def fibonacci(n: int) -> int:
    if n < 0:
        raise NegativeParameterError("n must be >= 0")
    if n in (0, 1):
        return n
    a, b = 0, 1
    for _ in range(2, n):
        a, b = b, a + b
    return b


async def mean_handler(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    event = await receive()
    raw_body: bytes = event.get("body", b"")

    if not raw_body:
        return await _send_json(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "missing body"}
        )

    try:
        data = json.loads(raw_body.decode())
    except json.JSONDecodeError:
        return await _send_json(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "invalid JSON"}
        )

    if not isinstance(data, list):
        return await _send_json(
            send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "body must be list"}
        )

    if not data:
        return await _send_json(send, HTTPStatus.BAD_REQUEST, {"error": "empty list"})

    if not all(isinstance(x, (int, float)) for x in data):
        return await _send_json(
            send,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {"error": "list must contain only numbers"},
        )

    result = mean([float(x) for x in data])
    return await _send_json(send, HTTPStatus.OK, {"result": result})


def mean(lst: list[float]) -> float:
    return sum(lst) / len(lst)


routes: dict[str, Callable] = {
    "factorial": factorial_handler,
    "fibonacci": fibonacci_handler,
    "mean": mean_handler,
}


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
    if scope["type"] == "http":

        path = scope["path"].strip("/").split("/")
        route = path[0] if path else ""

        handler: Callable | None = routes.get(route)
        if handler is None:
            await send(
                {
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [[b"content-type", b"text/plain"]],
                }
            )
            await send({"type": "http.response.body", "body": b"Not found"})
            return

        await handler(scope, receive, send)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
