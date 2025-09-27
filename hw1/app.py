from typing import Any, Awaitable, Callable
import json
import math


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
    # Проверяем, что это HTTP запрос
    if scope["type"] != "http":
        return

    # Получаем метод и путь
    method = scope["method"]
    path = scope["path"]

    # Обрабатываем только GET запросы
    if method != "GET":
        await send_error(send, 405, "Method Not Allowed")
        return

    # Разбираем путь и параметры
    if path.startswith("/fibonacci/"):
        await handle_fibonacci(scope, send)
    elif path == "/factorial":
        await handle_factorial(scope, send)
    elif path == "/mean":
        await handle_mean(scope, send)
    else:
        await send_error(send, 404, "Not Found")


async def handle_fibonacci(scope: dict[str, Any], send: Callable):
    """Обработка /fibonacci/{n}"""
    try:
        # Извлекаем n из пути
        path = scope["path"]
        n_str = path.split("/fibonacci/")[1]
        n = int(n_str)

        if n < 0:
            await send_error(send, 400, "n must be non-negative")
            return

        # Вычисляем n-е число Фибоначчи
        result = fibonacci(n)
        await send_response(send, 200, {"result": result})

    except (ValueError, IndexError):
        await send_error(send, 400, "Invalid parameter n")


async def handle_factorial(scope: dict[str, Any], send: Callable):
    """Обработка /factorial?n=5"""
    try:
        # Извлекаем параметр n из query string
        query_string = scope.get("query_string", b"").decode()
        params = parse_query_string(query_string)
        n_str = params.get("n", [""])[0]

        if not n_str:
            await send_error(send, 400, "Missing parameter n")
            return

        n = int(n_str)

        if n < 0:
            await send_error(send, 400, "n must be non-negative")
            return

        # Вычисляем факториал
        result = math.factorial(n)
        await send_response(send, 200, {"result": result})

    except ValueError:
        await send_error(send, 400, "Invalid parameter n")


async def handle_mean(scope: dict[str, Any], send: Callable):
    """Обработка /mean?numbers=1,2,3"""
    try:
        # Извлекаем параметр numbers из query string
        query_string = scope.get("query_string", b"").decode()
        params = parse_query_string(query_string)
        numbers_str = params.get("numbers", [""])[0]

        if not numbers_str:
            await send_error(send, 400, "Missing parameter numbers")
            return

        # Парсим числа
        numbers = [float(x) for x in numbers_str.split(",")]

        if not numbers:
            await send_error(send, 400, "Empty numbers list")
            return

        # Вычисляем среднее арифметическое
        result = sum(numbers) / len(numbers)
        await send_response(send, 200, {"result": result})

    except (ValueError, ZeroDivisionError):
        await send_error(send, 400, "Invalid numbers format")


def fibonacci(n: int) -> int:
    """Вычисляет n-е число Фибоначчи"""
    if n == 0:
        return 0
    elif n == 1:
        return 1

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def parse_query_string(query_string: str) -> dict:
    """Парсит query string в словарь параметров"""
    params = {}
    if not query_string:
        return params

    for pair in query_string.split("&"):
        if "=" in pair:
            key, value = pair.split("=", 1)
            if key not in params:
                params[key] = []
            params[key].append(value)

    return params


async def send_response(send: Callable, status: int, data: dict):
    """Отправляет успешный JSON ответ"""
    body = json.dumps(data).encode("utf-8")

    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })

    await send({
        "type": "http.response.body",
        "body": body,
    })


async def send_error(send: Callable, status: int, message: str):
    """Отправляет ошибку"""
    body = json.dumps({"error": message}).encode("utf-8")

    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })

    await send({
        "type": "http.response.body",
        "body": body,
    })


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)