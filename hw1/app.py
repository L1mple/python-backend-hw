from http import HTTPStatus
from numbers import Number
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import json


def fibonacci(n: int) -> int:
    if n in (0, 1):
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def factorial(n: int) -> int:
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def mean(lst: list[float]) -> float:
    return sum(lst) / len(lst)


def validate_qp(n: str):
    result = None

    if n is None:
        result = (HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "missing 'n' param"})
    elif n[0] == '-':
        result = (HTTPStatus.BAD_REQUEST, {"error": "n must be non-negative"})
    elif not n.isdigit():
        result = (HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "n must be integer"})

    return result


def validate_body(data: str):
    result = None

    if not isinstance(data, list):
        result = (HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "unreachable body, must be list"})
    elif not len(data):
        result = (HTTPStatus.BAD_REQUEST, {"error": "unreachable empty list as body"})
    elif not all(isinstance(x, Number) for x in data):
        result = (HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "unreachable values in body, must be only numbers"})

    return result


async def json_response(status: int, payload: dict[str, Any], send: Callable[[dict[str, Any]], Awaitable[None]]):
    body = json.dumps(payload).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", b"application/json"]],
    })
    await send({"type": "http.response.body", "body": body})


async def fibonacci_handler(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    parts = scope["path"].strip("/").split("/")
    n = parts[1]
    validate_result = validate_qp(n)

    if validate_result is not None:
        status, payload = validate_result
        return await json_response(status, payload, send)

    result = fibonacci(int(n))
    return await json_response(HTTPStatus.OK, {"result": result}, send)


async def factorial_handler(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    params = {k: v[0] for k, v in parse_qs(scope["query_string"].decode()).items()}
    n = params.get("n")
    validate_result = validate_qp(n)

    if validate_result is not None:
        status, payload = validate_result
        return await json_response(status, payload, send)

    result = factorial(int(n))
    return await json_response(HTTPStatus.OK, {"result": result}, send)


async def mean_handler(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    message = await receive()
    body = message.get("body").decode()
    data = json.loads(body)
    validate_result = validate_body(data)

    if validate_result is not None:
        status, payload = validate_result
        return await json_response(status, payload, send)

    result = mean([float(x) for x in data])
    return await json_response(HTTPStatus.OK, {"result": result}, send)


async def not_found_handler(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    await send({
        "type": "http.response.start",
        "status": HTTPStatus.NOT_FOUND,
        "headers": [[b"content-type", b"text/plain"]],
    })
    await send({"type": "http.response.body", "body": b"Not found"})


async def handle_lifespan(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    while True:
        message = await receive()
        if message['type'] == 'lifespan.startup':
            await send({'type': 'lifespan.startup.complete'})
        elif message['type'] == 'lifespan.shutdown':
            await send({'type': 'lifespan.shutdown.complete'})
            return


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
        await handle_lifespan(scope, receive, send)
    elif scope["type"] == "http":
        action = scope["path"].strip("/").split("/")[0]
        handler = None

        if action == "fibonacci" and scope["method"] == "GET":
            handler = fibonacci_handler
        elif action == "factorial" and scope["method"] == "GET":
            handler = factorial_handler
        elif action == "mean" and scope["method"] == "GET":
            handler = mean_handler

        if not handler:
            return await not_found_handler(scope, receive, send)

        await handler(scope, receive, send)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
