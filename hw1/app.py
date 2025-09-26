from typing import Any, Awaitable, Callable
from http import HTTPStatus
import json


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
def factorial_endpoint(n_raw) -> int | HTTPStatus:
    try:
        n = int(n_raw[2:])
        if n < 0:
            return HTTPStatus.BAD_REQUEST
    except ValueError:
        return HTTPStatus.UNPROCESSABLE_CONTENT
    return factorial(n)


def fibonacci_endpoint(n_raw) -> int | HTTPStatus:
    try:
        n = int(n_raw)
        if n < 0:
            return HTTPStatus.BAD_REQUEST
    except ValueError:
        return HTTPStatus.UNPROCESSABLE_CONTENT
    return fibonacci(n)


def mean_endpoint(numbers_raw) -> float | HTTPStatus:
    try:
        numbers = [float(number) for number in numbers_raw[8:].split(",")]
    except ValueError:
        return HTTPStatus.UNPROCESSABLE_CONTENT
    return mean(numbers)


ENDPOINTS = {
    "factorial": factorial_endpoint,
    "fibonacci": fibonacci_endpoint,
    "mean": mean_endpoint,
}
###


def parse_query(path: str, query_string: str) -> tuple[str, str]:
    parts = path.split("/")
    if len(parts) == 3:
        # return endpoint and params
        return (parts[1], parts[2])
    else:
        # return endpoint and cgi params
        return (parts[1], query_string)


def get_endpoint(scope: dict[str, Any]) -> Callable[[...], Any]:
    path = scope["path"]
    query_string = scope["query_string"].decode()
    endpoint, params = parse_query(path, query_string)
    try:
        func = ENDPOINTS[endpoint]
    except KeyError:
        return -1, HTTPStatus.NOT_FOUND

    result = func(params)
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

    result, status = get_endpoint(scope)
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
