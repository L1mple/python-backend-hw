import json
import math
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs, urlparse
import json


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
    if scope["type"] != "http":
        await send_422(send, "Invalid request")
        return

    query_string = scope["query_string"]
    method = scope["method"]
    path = scope["path"]
    
    # Парсим URL и query параметры
    parsed_url = urlparse(path)
    query_params = parse_qs(query_string, encoding="utf-8")
    
    # Получаем тело запроса для эндпоинта /mean
    body = b""
    if path.startswith("/mean"):
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
    
    # Определяем эндпоинт и обрабатываем запрос
    if method == "GET":
        if path.startswith("/fibonacci/"):
            await handle_fibonacci(parsed_url.path, send)
        elif path.startswith("/factorial"):
            await handle_factorial(query_params, send)
        elif path.startswith("/mean"):
            await handle_mean(body, send)
        else:
            await send_404(send)
    else:
        await send_404(send)


async def handle_fibonacci(path: str, send: Callable[[dict[str, Any]], Awaitable[None]]):
    """Обработка эндпоинта /fibonacci/{n}"""
    try:
        # Извлекаем n из пути
        n_str = path.split("/fibonacci/")[1]
        n = int(n_str)
        
        if n < 0:
            await send_400(send, "Negative numbers not allowed")
            return
        
        # Вычисляем число Фибоначчи
        result = fibonacci(n)
        await send_200(send, {"result": result})
        
    except ValueError:
        await send_422(send, "Invalid number format")
    except Exception:
        await send_422(send, "Invalid request")


async def handle_factorial(query_params: dict, send: Callable[[dict[str, Any]], Awaitable[None]]):
    """Обработка эндпоинта /factorial?n={n}"""
    try:
        if b"n" not in query_params.keys():
            await send_422(send, "Missing parameter 'n'")
            return
        
        n_str = query_params[b"n"][0]
        if not n_str:
            await send_422(send, "Empty parameter 'n'")
            return
        
        n = int(n_str)
        
        if n < 0:
            await send_400(send, "Negative numbers not allowed")
            return
        
        # Вычисляем факториал
        result = math.factorial(n)
        await send_200(send, {"result": result})
        
    except ValueError:
        await send_422(send, "Invalid number format")
    except Exception:
        await send_422(send, "Invalid request")


async def handle_mean(body: bytes, send: Callable[[dict[str, Any]], Awaitable[None]]):
    """Обработка эндпоинта /mean"""
    try:
        # Если тело запроса пустое, возвращаем 422
        if not body:
            await send_422(send, "Missing request body")
            return
        
        # Парсим JSON из тела запроса
        try:
            numbers_list = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            await send_422(send, "Invalid JSON format")
            return
        
        # Проверяем, что это список
        if not isinstance(numbers_list, list):
            await send_422(send, "Expected array")
            return
        
        # Если список пустой, возвращаем 400
        if len(numbers_list) == 0:
            await send_400(send, "Empty array")
            return
        
        # Проверяем, что все элементы - числа
        try:
            numbers_list = [float(x) for x in numbers_list]
        except (ValueError, TypeError):
            await send_422(send, "All elements must be numbers")
            return
        
        # Вычисляем среднее арифметическое
        result = sum(numbers_list) / len(numbers_list)
        await send_200(send, {"result": result})

    except Exception:
        await send_422(send, "Invalid request")


def fibonacci(n: int) -> int:
    """Вычисление n-го числа Фибоначчи"""
    if n <= 1:
        return n
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    
    return b


async def send_200(send: Callable[[dict[str, Any]], Awaitable[None]], data: dict):
    """Отправка успешного ответа (200 OK)"""
    response_body = json.dumps(data).encode()
    
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(response_body)).encode()],
        ],
    })
    
    await send({
        "type": "http.response.body",
        "body": response_body,
    })


async def send_400(send: Callable[[dict[str, Any]], Awaitable[None]], message: str):
    """Отправка ошибки 400 Bad Request"""
    response_body = json.dumps({"error": message}).encode()
    
    await send({
        "type": "http.response.start",
        "status": 400,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(response_body)).encode()],
        ],
    })
    
    await send({
        "type": "http.response.body",
        "body": response_body,
    })


async def send_404(send: Callable[[dict[str, Any]], Awaitable[None]]):
    """Отправка ошибки 404 Not Found"""
    response_body = json.dumps({"error": "Not Found"}).encode()
    
    await send({
        "type": "http.response.start",
        "status": 404,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(response_body)).encode()],
        ],
    })
    
    await send({
        "type": "http.response.body",
        "body": response_body,
    })


async def send_422(send: Callable[[dict[str, Any]], Awaitable[None]], message: str):
    """Отправка ошибки 422 Unprocessable Entity"""
    response_body = json.dumps({"error": message}).encode()
    
    await send({
        "type": "http.response.start",
        "status": 422,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(response_body)).encode()],
        ],
    })
    
    await send({
        "type": "http.response.body",
        "body": response_body,
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
