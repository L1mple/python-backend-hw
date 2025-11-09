import json
import math
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


def factorial(n: int) -> int:
    """Вычисление факториала числа n."""
    if n == 0:
        return 1
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def fibonacci(n: int) -> int:
    """Вычисление n-го числа Фибоначчи."""
    if n == 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def mean(numbers: list[int | float]) -> float:
    """Вычисление среднего арифметического."""
    return sum(numbers) / len(numbers)


async def send_response(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    body: dict[str, Any] | None = None,
):
    """Отправка HTTP ответа."""
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", b"application/json"]],
    })
    
    response_body = json.dumps(body if body else {}).encode("utf-8")
    await send({
        "type": "http.response.body",
        "body": response_body,
    })


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
    # Обработка lifespan событий
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return
    
    # Парсинг запроса
    if scope["type"] != "http":
        return
    
    method = scope["method"]
    path = scope["path"]
    query_string = scope.get("query_string", b"").decode("utf-8")
    
    # Роутинг
    if method == "GET" and path == "/factorial":
        # Обработка /factorial
        query_params = parse_qs(query_string)
        
        if "n" not in query_params or not query_params["n"][0]:
            await send_response(send, 422, {"error": "Missing or empty parameter n"})
            return
        
        try:
            n = int(query_params["n"][0])
        except ValueError:
            await send_response(send, 422, {"error": "Parameter n must be an integer"})
            return
        
        if n < 0:
            await send_response(send, 400, {"error": "Parameter n must be non-negative"})
            return
        
        result = factorial(n)
        await send_response(send, 200, {"result": result})
        return
    
    elif method == "GET" and path.startswith("/fibonacci/"):
        # Обработка /fibonacci/{n}
        try:
            n_str = path.split("/fibonacci/")[1]
            n = int(n_str)
        except (IndexError, ValueError):
            await send_response(send, 422, {"error": "Invalid parameter n"})
            return
        
        if n < 0:
            await send_response(send, 400, {"error": "Parameter n must be non-negative"})
            return
        
        result = fibonacci(n)
        await send_response(send, 200, {"result": result})
        return
    
    elif method == "GET" and path == "/mean":
        # Обработка /mean
        body_bytes = b""
        while True:
            message = await receive()
            if message["type"] == "http.request":
                body_bytes += message.get("body", b"")
                if not message.get("more_body", False):
                    break
        
        if not body_bytes:
            await send_response(send, 422, {"error": "Request body is required"})
            return
        
        try:
            body_data = json.loads(body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            await send_response(send, 422, {"error": "Invalid JSON"})
            return
        
        if not isinstance(body_data, list):
            await send_response(send, 422, {"error": "Body must be an array"})
            return
        
        if len(body_data) == 0:
            await send_response(send, 400, {"error": "Array must not be empty"})
            return
        
        # Проверка что все элементы - числа
        if not all(isinstance(x, (int, float)) and not isinstance(x, bool) for x in body_data):
            await send_response(send, 422, {"error": "All elements must be numbers"})
            return
        
        result = mean(body_data)
        await send_response(send, 200, {"result": result})
        return
    
    # 404 для всех остальных путей
    await send_response(send, 404, {"error": "Not found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
