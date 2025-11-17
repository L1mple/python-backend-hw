from typing import Any, Awaitable, Callable, Dict, List
import json


async def application(
    scope: Dict[str, Any],
    receive: Callable[[], Awaitable[Dict[str, Any]]],
    send: Callable[[Dict[str, Any]], Awaitable[None]],
):
    """
    Args:
        scope: Словарь с информацией о запросе
        receive: Корутина для получения сообщений от клиента
        send: Корутина для отправки сообщений клиенту
    """
    # Обрабатываем lifespan события (startup/shutdown)
    if scope["type"] == "lifespan":
        await handle_lifespan(scope, receive, send)
        return
    
    # Проверяем, что это HTTP запрос
    if scope["type"] != "http":
        return

    # Получаем метод и путь запроса
    method = scope["method"]
    path = scope["path"]

    # Обрабатываем только GET запросы
    if method != "GET":
        await send_response(send, 404, {"error": "Not found"})
        return

    # Обрабатываем разные эндпоинты
    if path == "/factorial":
        await handle_factorial(scope, receive, send)
    elif path.startswith("/fibonacci/"):
        await handle_fibonacci(scope, receive, send)
    elif path == "/mean":
        await handle_mean(scope, receive, send)
    else:
        await send_response(send, 404, {"error": "Not found"})


async def handle_lifespan(scope: Dict[str, Any], receive: Callable, send: Callable):
    """Обработчик lifespan событий (startup/shutdown)"""
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return


async def send_response(send: Callable, status: int, data: Dict[str, Any]):
    """Вспомогательная функция для отправки ответа"""
    response_body = json.dumps(data).encode("utf-8")
    
    # Отправляем заголовки
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })
    
    # Отправляем тело
    await send({
        "type": "http.response.body",
        "body": response_body,
    })


async def handle_factorial(scope: Dict[str, Any], receive: Callable, send: Callable):
    """Обработчик для факториала"""
    query_string = scope.get("query_string", b"").decode("utf-8")
    params = parse_query_string(query_string)
    
    n_str = params.get("n", [""])[0]
    
    # Валидация параметра n
    if not n_str:
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    # Проверяем, что это целое число
    if not is_integer_string(n_str):
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    n = int(n_str)
    if n < 0:
        await send_response(send, 400, {"error": "Bad request"})
        return
    
    # Вычисляем факториал
    result = factorial(n)
    await send_response(send, 200, {"result": result})


async def handle_fibonacci(scope: Dict[str, Any], receive: Callable, send: Callable):
    """Обработчик для чисел Фибоначчи"""
    path = scope["path"]
    
    # Извлекаем n из пути /fibonacci/{n}
    n_str = path.split("/")[-1]
    
    if not n_str:
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    # Проверяем, что это целое число
    if not is_integer_string(n_str):
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    n = int(n_str)
    if n < 0:
        await send_response(send, 400, {"error": "Bad request"})
        return
    
    # Вычисляем n-ное число Фибоначчи
    result = fibonacci(n)
    await send_response(send, 200, {"result": result})


async def handle_mean(scope: Dict[str, Any], receive: Callable, send: Callable):
    """Обработчик для среднего арифметического"""
    # Получаем тело запроса
    body = await receive_body(receive)
    
    if not body:
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    try:
        numbers = json.loads(body)
    except json.JSONDecodeError:
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    if not isinstance(numbers, list):
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    if not numbers:
        await send_response(send, 400, {"error": "Bad request"})
        return
    
    # Проверяем, что все элементы списка - числа
    if not all(isinstance(x, (int, float)) for x in numbers):
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    # Вычисляем среднее арифметическое
    try:
        mean = sum(numbers) / len(numbers)
    except TypeError:
        await send_response(send, 422, {"error": "Unprocessable entity"})
        return
    
    await send_response(send, 200, {"result": mean})


async def receive_body(receive: Callable) -> str:
    """Получает тело запроса"""
    body = b""
    more_body = True
    
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    
    return body.decode("utf-8")


def parse_query_string(query_string: str) -> Dict[str, List[str]]:
    """Парсит query string в словарь параметров"""
    params: Dict[str, List[str]] = {}
    if query_string:
        for param in query_string.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                if key in params:
                    params[key].append(value)
                else:
                    params[key] = [value]
            else:
                # Обрабатываем параметры без значения
                if param in params:
                    params[param].append("")
                else:
                    params[param] = [""]
    return params


def is_integer_string(s: str) -> bool:
    """Проверяет, является ли строка целым числом"""
    if not s:
        return False
    if s[0] in ('-', '+'):
        return s[1:].isdigit()
    return s.isdigit()


def factorial(n: int) -> int:
    """Вычисляет факториал числа """
    if n == 0:
        return 1
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def fibonacci(n: int) -> int:
    """Вычисляет n-ное число Фибоначчи"""
    if n == 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)