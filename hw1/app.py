from typing import Any, Awaitable, Callable
from http import HTTPStatus
import json
from urllib.parse import urlparse


# Math backend
def factorial(n: int) -> int:
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def fibonacci(n: int) -> int:
    if n == 0:
        return 0
    if n == 1:
        return 1

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def mean(numbers: list[float]) -> float:
    return sum(numbers) / len(numbers)


###


# Endpoints
def factorial_endpoint(params: str, data: Any) -> int | HTTPStatus:
    try:
        n = int(params[2:])
        if n < 0:
            return HTTPStatus.BAD_REQUEST
    except ValueError:
        return HTTPStatus.UNPROCESSABLE_CONTENT
    return factorial(n)


def fibonacci_endpoint(params: str, data: Any) -> int | HTTPStatus:
    try:
        n = int(params)
        if n < 0:
            return HTTPStatus.BAD_REQUEST
    except ValueError:
        return HTTPStatus.UNPROCESSABLE_CONTENT
    return fibonacci(n)


def mean_endpoint(params: str, data: bytes) -> float | HTTPStatus:
    # Expect JSON array in the request body
    if not data:
        return HTTPStatus.UNPROCESSABLE_ENTITY
    try:
        payload = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return HTTPStatus.UNPROCESSABLE_ENTITY

    if payload is None:
        return HTTPStatus.UNPROCESSABLE_ENTITY
    if not isinstance(payload, list):
        return HTTPStatus.UNPROCESSABLE_ENTITY
    if len(payload) == 0:
        return HTTPStatus.BAD_REQUEST

    try:
        numbers = [float(value) for value in payload]
    except (TypeError, ValueError):
        return HTTPStatus.BAD_REQUEST

    return mean(numbers)


ENDPOINTS = {
    "factorial": factorial_endpoint,
    "fibonacci": fibonacci_endpoint,
    "mean": mean_endpoint,
}
###


def get_endpoint_name(scope: dict[str, Any]) -> str:
    """Return endpoint name (first path segment) using urlparse."""
    path = scope["path"]
    parsed = urlparse(path)
    clean_path = parsed.path.strip("/")
    if not clean_path:
        return ""
    first, *_ = clean_path.split("/", 1)
    return first


def get_param_from_url(scope: dict[str, Any]) -> str:
    """Return the parameter part: path segment if present, else the raw query string.

    This preserves existing behavior where factorial expects a raw
    "n=..." style string and fibonacci expects the second path segment.
    """
    path = scope["path"]
    parsed = urlparse(path)
    clean_path = parsed.path.strip("/")
    parts = clean_path.split("/") if clean_path else []
    if len(parts) >= 2 and parts[1]:
        return parts[1]
    # fallback to decoded query string (without '?')
    return scope.get("query_string", b"").decode()


def execute_endpoint(scope: dict[str, Any], data: Any) -> Callable[[...], Any]:
    endpoint = get_endpoint_name(scope)
    params = get_param_from_url(scope)
    try:
        func = ENDPOINTS[endpoint]
    except KeyError:
        return -1, HTTPStatus.NOT_FOUND

    result = func(params, data)
    if isinstance(result, HTTPStatus):
        return -1, result
    else:
        return result, HTTPStatus.OK


async def read_request_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    body = b""
    while True:
        message = await receive()
        if message["type"] != "http.request":
            # Ignore non-http.request messages for robustness
            continue
        body += message.get("body", b"")
        if not message.get("more_body"):
            break
    return body


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
    # TODO: Ваша реализация здесь

    # Handle lifespan events
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            msg_type = message.get("type")
            if msg_type == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg_type == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    # Only HTTP requests below
    if scope["type"] != "http":
        # Not supported scope
        await send({"type": "http.response.start", "status": int(HTTPStatus.NOT_FOUND)})
        await send({"type": "http.response.body", "body": b""})
        return

    # Handle only correct methods
    method = scope["method"]
    if method != "GET":
        await send(
            {
                "type": "http.response.start",
                "status": int(HTTPStatus.NOT_FOUND),
                "headers": [],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": b"",
                "headers": [(b"content-type", b"application/json")],
            }
        )
        return

    data = await read_request_body(receive)
    result, status = execute_endpoint(scope, data)
    await send(
        {
            "type": "http.response.start",
            "status": int(status),
            "headers": [],
        }
    )
    if status != HTTPStatus.OK:
        result = {}
    await send(
        {
            "type": "http.response.body",
            "body": json.dumps({"result": result}).encode(),
            "headers": [(b"content-type", b"application/json")],
        }
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
