from typing import Any, Awaitable, Callable
from http import HTTPStatus
import json
from math import factorial

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
    # Обрабатываем lifespan-запросы (startup/shutdown)
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    await handle_http_request(scope, receive, send)


async def handle_http_request(scope, receive, send):
    method = scope["method"]
    path = scope["path"]

    if method == "GET":

        # Ручка для fibonacci
        if path.startswith("/fibonacci/"):
            number_str = path.split("/fibonacci/")[1]
            try:
                n = int(number_str)
            except:
                await send_json_response(send, {"error": "Invalid parameter"}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return

            if n < 0:
                await send_json_response(send, {"error": "Invalid parameter"}, HTTPStatus.BAD_REQUEST)
                return

            result = await fibonacci(n)
            await send_json_response(send, {"result": result}, HTTPStatus.OK)
            return

        # Ручка для factorial
        if path.startswith("/factorial"):
            query_string = scope.get("query_string", b"").decode()
            params = {}
            if query_string:
                for param in query_string.split("&"):
                    if "=" in param:
                        key, value = param.split("=", 1)
                        params[key] = value

            if "n" not in params:
                await send_json_response(send, {"error": "Missing parameter 'n'"}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return

            n_str = params["n"]

            # Проверяем что параметр не пустой
            if n_str == "":
                await send_json_response(send, {"error": "Invalid parameter"}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            try:
                n = int(n_str)
            except :
                await send_json_response(send, {"error": "Invalid number parameter"}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return

                # Проверяем что число не отрицательное
            if n < 0:
                await send_json_response(send, {"error": "Number must be non-negative"}, HTTPStatus.BAD_REQUEST)
                return

            result = factorial(n)
            await send_json_response(send, {"result": result}, HTTPStatus.OK)
            return

        # Ручка для mean
        if path.startswith("/mean"):

            body = await receive_body(receive)
            if body is None:
                await send_json_response(send, {"error": "No JSON data"}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return

            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                await send_json_response(send, {"error": "Invalid JSON"}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return

            # Проверяем что данные - это список
            if not isinstance(data, list):
                await send_json_response(send, {"error": "Data must be a list"}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return

            # Проверяем что список не пустой
            if len(data) == 0:
                await send_json_response(send, {"error": "List cannot be empty"}, HTTPStatus.BAD_REQUEST)
                return

            # Проверяем что все элементы - числа
            if not all(isinstance(x, (int, float)) for x in data):
                await send_json_response(send, {"error": "All elements must be numbers"}, HTTPStatus.UNPROCESSABLE_ENTITY)
                return

            # Вычисляем среднее значение
            result = sum(data) / len(data)
            await send_json_response(send, {"result": result}, HTTPStatus.OK)
            return

    await send_json_response(send, {"error": "Not available"}, HTTPStatus.NOT_FOUND)
    return

async def receive_body(receive):
    """Получает тело запроса"""
    body = b""
    more_body = True

    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    return body.decode('utf-8') if body else None


async def send_json_response(send, data: dict, status_code: HTTPStatus):
    """Универсальная функция для отправки JSON ответов"""
    body = json.dumps(data).encode()

    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": [[b"content-type", b"application/json"]]
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })
    return

async def fibonacci(n: int) -> int:
    """Вычисляет n-ное число Фибоначчи"""
    if n < 0:
        raise ValueError("Number must be non-negative")
    if n <= 1:
        return n

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
