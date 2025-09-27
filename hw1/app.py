from typing import Any, Awaitable, Callable
import json
import math
from urllib.parse import parse_qs

def _fib(n: int) -> int:
    """Вычисляет n-е число Фибоначчи"""
    if n == 0:
        return 0
    elif n == 1:
        return 1
    previous, current = 0, 1
    for _ in range(2, n + 1):
        previous, current = current, previous + current
    return current


def _factorial(n: int) -> int:
    """Вычисляет факториал n"""
    return math.factorial(n)


def _mean(numbers: list[float]) -> float:
    """Вычисляет среднее арифметическое списка чисел"""
    total = sum(numbers)
    count = len(numbers)
    return total / count if count > 0 else 0.0


def factorial_query(query_params: dict[str, list[str]]) -> tuple[int, dict[str, Any]]:
    """Обрабатывает запрос на вычисление факториала"""
    n_values = query_params.get("n", [])
    if len(n_values) > 1:
        return 422, {"error": "Multiple values for 'n' parameter are not supported"}
    if not n_values:
        return 422, {"error": "The 'n' parameter is required for factorial calculation"}
    try:
        n = int(n_values[0])
        if n < 0:
            return 400, {"error": "The factorial operation requires a non-negative number"}
        else:
            result = _factorial(n)
            return 200, {"result": result}
    except ValueError:
        return 422, {"error": "The 'n' parameter must be an integer"}


def fibonacci_query(path: str) -> tuple[int, dict[str, Any]]:
    """Обрабатывает запрос на вычисление числа Фибоначчи"""
    try:
        n = int(path.split("/")[-1])
        if n < 0:
            return 400, {"error": "Fibonacci sequence is only defined for non-negative indices"}
        else:
            result = _fib(n)
            return 200, {"result": result}
    except ValueError:
        return 422, {"error": "Please provide a valid integer for the Fibonacci calculation"}


def mean_query(body: bytes) -> tuple[int, dict[str, Any]]:
    """Обрабатывает запрос на вычисление среднего арифметического"""
    try:
        if not body:
            raise ValueError("No body")
        numbers = json.loads(body.decode())
        if not isinstance(numbers, list):
            return 422, {"error": "Input must be a JSON array"}
        if not numbers:
            return 400, {"error": "Cannot process an empty array for mean calculation"}
        if not all(isinstance(x, (int, float)) for x in numbers):
            return 422, {"error": "All elements in the array must be numeric values"}
        else:
            result = _mean(numbers)
            return 200, {"result": result}
    except (json.JSONDecodeError, TypeError, ValueError):
        return 422, {"error": "Please provide a valid JSON array containing only numbers"}


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
    
    if scope["type"] != "http":
        return
    
    method = scope["method"]
    path = scope["path"]
    query_string = scope.get("query_string", b"").decode()
    query_params = parse_qs(query_string)

    if method == "GET" and path == "/factorial":
        status, response_body = factorial_query(query_params)
    elif method == "GET" and (path == "/fibonacci" or path.startswith("/fibonacci/")):
        status, response_body = fibonacci_query(path)
    elif method == "GET" and path == "/mean":
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        status, response_body = mean_query(body)
    else:
        status = 404
        response_body = {"error": "The requested endpoint is not available"} 

    response_body_bytes = json.dumps(response_body).encode()
    headers = [("Content-Type", "application/json"), ("Content-Length", str(len(response_body_bytes)))]

    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(k.encode(), v.encode()) for k, v in headers],
    })

    await send({
        "type": "http.response.body",
        "body": response_body_bytes,
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app_original:application", host="0.0.0.0", port=8000, reload=True)
