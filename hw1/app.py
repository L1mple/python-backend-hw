from typing import Any, Awaitable, Callable
from dataclasses import dataclass
import math
import statistics
import json
from urllib.parse import parse_qs

fibonacci_array = [0, 1]


@dataclass
class int_model:
    n: int

    def fibonacci(self) -> int:
        while len(fibonacci_array) <= self.n:
            next_fib = fibonacci_array[-1] + fibonacci_array[-2]
            fibonacci_array.append(next_fib)

        return fibonacci_array[self.n]

    def factorial(self) -> int:
        result = math.factorial(self.n)
        return result


@dataclass
class mean_model:
    n: list[float]

    def mean(self) -> float:
        result = statistics.mean(self.n)
        return result


async def send_json_response(send, status_code, data):
    """Отправляет ответ"""
    response_body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                [b"content-type", b"application/json"],
                [b"content-length", str(len(response_body)).encode()],
            ],
        }
    )

    await send(
        {
            "type": "http.response.body",
            "body": response_body,
        }
    )


async def send_error_response(send, status_code, error_message):
    """Отправляет ответ с ошибкой"""
    await send_json_response(send, status_code, {"error": error_message})


async def get_request_body(receive):
    """Получает тело запроса"""
    body = b""
    while True:
        message = await receive()
        if message["type"] == "http.request":
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
    return body


async def route_fibonacci(send, path: str):
    """GET /fibonacci/{n} - возвращает n-е число Фибоначчи"""
    n_str = path.split("/fibonacci/")[-1]

    try:
        n = int(n_str)
        if n < 0:
            await send_error_response(send, 400, "n should be greater or equal to 0")
            return
        result = int_model(n=n).fibonacci()
        await send_json_response(send, 200, {"result": result})
    except ValueError:
        await send_error_response(send, 422, "Invalid number format")
    except AssertionError as e:
        await send_error_response(send, 400, str(e))


async def route_factorial(send, query_params: dict):
    """GET /factorial?n=число - возвращает факториал числа"""

    if "n" not in query_params:
        await send_error_response(send, 422, "Parameter 'n' is required")
        return

    try:
        n = int(query_params["n"][0])
        if n < 0:
            await send_error_response(send, 400, "n should be greater or equal to 0")
            return
        result = int_model(n=n).factorial()
        await send_json_response(send, 200, {"result": result})
    except ValueError:
        await send_error_response(send, 422, "Invalid number format")
    except AssertionError as e:
        await send_error_response(send, 400, str(e))


async def route_mean(send, receive):
    """GET /mean с JSON body - возвращает среднее арифметическое"""

    body = await get_request_body(receive)
    if not body:
        await send_error_response(send, 422, "JSON body is required")
        return
    try:
        data = json.loads(body.decode("utf-8"))

        if not isinstance(data, list):
            await send_error_response(send, 422, "Expected a list of numbers")
            return

        if len(data) == 0:
            await send_error_response(send, 400, "Numbers list cannot be empty")
            return

        numbers = [float(item) for item in data]
        result = mean_model(n=numbers).mean()
        await send_json_response(send, 200, {"result": result})

    except json.JSONDecodeError:
        await send_error_response(send, 422, "Invalid JSON format")
    except (ValueError, TypeError):
        await send_error_response(send, 422, "All elements must be numbers")


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
                print("Application is starting up...")
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                print("Application is shutting down...")
                await send({"type": "lifespan.shutdown.complete"})
                return

    # Проверяем тип запроса
    if scope["type"] != "http":
        await send_error_response(send, 422, "Unsupported request type")
        return

    # Проверяем метод запроса
    if scope["method"] != "GET":
        await send_error_response(send, 404, "Method not allowed")
        return

    # Получаем данные запроса
    path = scope["path"]
    query_string = scope["query_string"].decode("utf-8")
    query_params = parse_qs(query_string) if query_string else {}

    try:
        match path:
            case p if p.startswith("/fibonacci/"):
                await route_fibonacci(send, path)

            case "/factorial":
                await route_factorial(send, query_params)

            case "/mean":
                await route_mean(send, receive)

            case _:
                await send_error_response(send, 404, "Endpoint not found")

    except Exception as e:
        await send_error_response(send, 500, f"Internal server error: {str(e)}")


if __name__ == "__main__":
    print("\n🚀 Запуск ASGI сервера...")
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
