import json
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


async def send_response(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    body: dict[str, Any],
) -> None:
    """Отправляет HTTP ответ клиенту"""
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": json.dumps(body).encode("utf-8"),
        }
    )


def is_integer_string(s: str) -> bool:
    """Проверяет, является ли строка целым числом"""
    if not s:
        return False

    if s[0] in ("-", "+"):
        return s[1:].isdigit()

    return s.isdigit()


def factorial(n: int) -> int:
    """Вычисляет факториал числа"""
    res = 1

    for i in range(2, n + 1):
        res *= i

    return res


def fibonacci(n: int) -> int:
    """Возвращает n-ное число Фибоначчи"""
    if n == 0:
        return 0
    elif n == 1:
        return 1

    a, b = 0, 1

    for _ in range(2, n + 1):
        a, b = b, a + b

    return b


async def receive_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> str:
    """Получает тело запроса"""
    body = b""
    more = True

    while more:
        msg = await receive()

        if msg.get("type") != "http.request":
            continue
        body += msg.get("body", b"")
        more = msg.get("more_body", False)

    return body.decode("utf-8")


# обработчики
async def handle_factorial(
    scope: dict[str, Any],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    query = parse_qs(scope.get("query_string", b"").decode("utf-8"))
    n_str = query.get("n", [""])[0]

    if not n_str or not is_integer_string(n_str):
        await send_response(send, 422, {"error": "Unprocessable"})
        return

    n = int(n_str)
    if n < 0:
        await send_response(send, 400, {"error": "Bad Request"})
        return

    await send_response(send, 200, {"result": factorial(n)})


async def handle_fibonacci(
    scope: dict[str, Any],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    parts = scope["path"].strip("/").split("/")

    if len(parts) != 2 or parts[0] != "fibonacci":
        await send_response(send, 404, {"error": "Not Found"})
        return

    n_str = parts[1]
    if not n_str or not is_integer_string(n_str):
        await send_response(send, 422, {"error": "Unprocessable"})
        return

    n = int(n_str)
    if n < 0:
        await send_response(send, 400, {"error": "Bad Request"})
        return

    await send_response(send, 200, {"result": fibonacci(n)})


async def handle_mean(
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    body_str = await receive_body(receive)

    if not body_str:
        await send_response(send, 422, {"error": "Unprocessable"})
        return

    try:
        numbers = json.loads(body_str)
    except json.JSONDecodeError:
        await send_response(send, 422, {"error": "Unprocessable"})
        return

    if not isinstance(numbers, list):
        await send_response(send, 422, {"error": "Unprocessable"})
        return

    if len(numbers) == 0:
        await send_response(send, 400, {"error": "Bad Request"})
        return

    if not all(isinstance(x, (int, float)) for x in numbers):
        await send_response(send, 422, {"error": "Unprocessable"})
        return

    await send_response(send, 200, {"result": sum(numbers) / len(numbers)})


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
            msg = await receive()
            if msg["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    if scope["type"] != "http":
        return

    method = scope["method"]
    path = scope["path"]

    # все методы пока что реализованы только для GET
    if method != "GET":
        await send_response(send, 404, {"error": "Not Found"})
        return

    if path.startswith("/fibonacci/"):
        await handle_fibonacci(scope, send)
    elif path == "/factorial":
        await handle_factorial(scope, send)
    elif path == "/mean":
        await handle_mean(receive, send)
    else:
        await send_response(send, 404, {"error": "Not Found"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
