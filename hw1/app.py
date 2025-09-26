import json
from http import HTTPStatus
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


async def send_json_response(send: Callable[[dict[str, Any]], Awaitable[None]], status_code: int, data: dict | None = None) -> None:
    """Отправляет JSON ответ"""
    body = json.dumps(data or {}).encode('utf-8')
    headers = [(b"content-type", b"application/json")]
    
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": headers
    })
    
    await send({
        "type": "http.response.body",
        "body": body
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
    # Проверяем, что это HTTP запрос
    if scope.get("type") != "http":
        return await send_json_response(send, HTTPStatus.NOT_FOUND)
    
    method = scope.get("method", "GET")
    path = scope.get("path", "/")
    
    # Эндпоинт /factorial?n=...
    if method == "GET" and path == "/factorial":
        # Парсим query параметры
        query_string = scope.get("query_string", b"").decode()
        params = parse_qs(query_string)
        
        # Проверяем наличие параметра n
        if "n" not in params or len(params["n"]) != 1:
            return await send_json_response(send, HTTPStatus.UNPROCESSABLE_ENTITY)
        
        try:
            n = int(params["n"][0])
        except ValueError:
            return await send_json_response(send, HTTPStatus.UNPROCESSABLE_ENTITY)
        
        if n < 0:
            return await send_json_response(send, HTTPStatus.BAD_REQUEST)
        
        # Вычисляем факториал
        result = 1
        for i in range(2, n + 1):
            result *= i
        
        return await send_json_response(send, HTTPStatus.OK, {"result": result})
    
    # Эндпоинт /fibonacci/{n}
    if method == "GET" and path.startswith("/fibonacci/"):
        # Извлекаем n из пути
        n_str = path.removeprefix("/fibonacci/")
        
        try:
            n = int(n_str)
        except ValueError:
            return await send_json_response(send, HTTPStatus.UNPROCESSABLE_ENTITY)
        
        if n < 0:
            return await send_json_response(send, HTTPStatus.BAD_REQUEST)
        
        # Вычисляем n-е число Фибоначчи
        if n == 0:
            result = 0
        elif n == 1:
            result = 1
        else:
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            result = b
        
        return await send_json_response(send, HTTPStatus.OK, {"result": result})
    
    # Эндпоинт /mean
    if method == "GET" and path == "/mean":
        # Читаем тело запроса
        body = b""
        while True:
            event = await receive()
            body += event.get("body", b"")
            if not event.get("more_body"):
                break
        
        if not body:
            return await send_json_response(send, HTTPStatus.UNPROCESSABLE_ENTITY)
        
        try:
            data = json.loads(body.decode())
        except json.JSONDecodeError:
            return await send_json_response(send, HTTPStatus.UNPROCESSABLE_ENTITY)
        
        if not isinstance(data, list):
            return await send_json_response(send, HTTPStatus.UNPROCESSABLE_ENTITY)
        
        if len(data) == 0:
            return await send_json_response(send, HTTPStatus.BAD_REQUEST)
        
        try:
            numbers = [float(x) for x in data]
        except (ValueError, TypeError):
            return await send_json_response(send, HTTPStatus.UNPROCESSABLE_ENTITY)
        
        # Вычисляем среднее
        mean_value = sum(numbers) / len(numbers)
        return await send_json_response(send, HTTPStatus.OK, {"result": mean_value})
    
    # Если ни один эндпоинт не подошел - 404
    return await send_json_response(send, HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
