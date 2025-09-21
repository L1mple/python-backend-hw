import json
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


async def read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    """Считывает всё тело HTTP запроса."""
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    return body


async def handle_factorial(query: dict[str, str], send: Callable[[dict[str, Any]], Awaitable[None]]):
    """
    Обрабатывает GET /factorial?n=<N>
    """
    n_str = query.get("n")
    if n_str is None:
        # параметр отсутствует → 422
        await send({"type": "http.response.start", "status": 422, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Unprocessable Entity"})
        return

    try:
        n = int(n_str)
    except ValueError:
        # не число → 422
        await send({"type": "http.response.start", "status": 422, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Unprocessable Entity"})
        return

    if n < 0:
        # отрицательное число → 400
        await send({"type": "http.response.start", "status": 400, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Bad Request"})
        return

    # вычисляем факториал
    result = 1
    for i in range(2, n + 1):
        result *= i

    response_body = json.dumps({"result": result}).encode("utf-8")
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": response_body})


async def handle_fibonacci(path: str, send: Callable[[dict[str, Any]], Awaitable[None]]):
    """
    Обрабатывает GET /fibonacci/{n}.
    - некорректный n (не число) → 422 Unprocessable Entity
    - n < 0 → 400 Bad Request
    - иначе → 200 + {"result": Fib(n)}
    """
    # path ожидаем вида "/fibonacci/10"
    _, _, n_str = path.partition("/fibonacci/")

    # проверяем, что n_str содержит число
    try:
        n = int(n_str)
    except ValueError:
        # некорректное число → 422
        await send({"type": "http.response.start", "status": 422, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Unprocessable Entity"})
        return

    if n < 0:
        # отрицательное число → 400
        await send({"type": "http.response.start", "status": 400, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Bad Request"})
        return

    # вычисляем N-й элемент Фибоначчи
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b

    response_body = json.dumps({"result": a}).encode("utf-8")
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": response_body})


async def handle_mean(body: bytes, send: Callable[[dict[str, Any]], Awaitable[None]]):
    """
    Логика для /mean (GET в тестах посылают тело JSON через GET).
    Требования (по тестам):
      - пустое тело (body == b'') => 422 Unprocessable Entity
      - пустой список => 400 Bad Request
      - корректный список чисел (или {"numbers": [...]}) => 200 и {"result": mean}
    """
    # 1) пустое тело => 422
    if not body:
        await send({"type": "http.response.start", "status": 422, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Unprocessable Entity"})
        return

    # 2) пробуем распарсить тело как JSON
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        await send({"type": "http.response.start", "status": 400, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Bad Request"})
        return

    # Проверяем, что данные не None
    if data is None:
        await send({"type": "http.response.start", "status": 422, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Unprocessable Entity"})
        return

    # 3) допускаем два варианта: список напрямую или {"numbers": [...]}
    if isinstance(data, list):
        numbers = data
    elif isinstance(data, dict):
        numbers = data.get("numbers")
    else:
        numbers = None

    # 4) проверки: numbers должен быть непустым списком
    if not isinstance(numbers, list):
        await send({"type": "http.response.start", "status": 400, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Bad Request"})
        return

    if len(numbers) == 0:
        await send({"type": "http.response.start", "status": 400, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Bad Request"})
        return

    # 5) вычисляем среднее
    try:
        mean_value = sum(float(x) for x in numbers) / len(numbers)
    except (TypeError, ValueError):
        # если элементы нельзя привести к float -> 400
        await send({"type": "http.response.start", "status": 400, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"Bad Request"})
        return

    response_body = json.dumps({"result": mean_value}).encode("utf-8")
    await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"application/json")]})
    await send({"type": "http.response.body", "body": response_body})


async def handle_not_found(send: Callable[[dict[str, Any]], Awaitable[None]]):
    """Отправляет 404 Not Found."""
    await send({"type": "http.response.start", "status": 404, "headers": [(b"content-type", b"text/plain")]})
    await send({"type": "http.response.body", "body": b"Not Found"})


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    path = scope.get("path", "")
    method = scope.get("method", "GET").upper()

    body = await read_body(receive)

    # Получаем query-параметры
    query_string = scope.get("query_string", b"").decode("utf-8")
    query_params = {k: v[0] for k, v in parse_qs(query_string).items()}

    if path == "/mean" and method == "GET":
        await handle_mean(body, send)
    elif path.startswith("/fibonacci") and method == "GET":
        await handle_fibonacci(path, send)
    elif path == "/factorial" and method == "GET":
        await handle_factorial(query_params, send)
    else:
        await handle_not_found(send)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
