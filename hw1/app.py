import math
import json
from http import HTTPStatus
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


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
        await send_error(send, HTTPStatus.BAD_REQUEST, "Only HTTP supported")
        return

    path = scope["path"]
    method = scope["method"]

    # Обработка различных маршрутов
    if method == "GET" and path == "/factorial":
        await handle_factorial(scope, receive, send)
    elif method == "GET" and path.startswith("/fibonacci/"):
        await handle_fibonacci(scope, receive, send)
    elif method in ["GET", "POST"] and path == "/mean":
        await handle_mean(scope, receive, send)  # Supporte GET et POST
    else:
        await send_error(send, HTTPStatus.NOT_FOUND, "Endpoint not found")


async def handle_factorial(scope, receive, send):
    """Обработка GET /factorial?n=5"""
    query_params = parse_query_string(scope["query_string"])
    n_str = query_params.get("n", [""])[0]
    
    # Cas limite: paramètre manquant
    if not n_str:
        await send_error(send, HTTPStatus.UNPROCESSABLE_ENTITY, "Missing parameter 'n'")
        return
    
    try:
        n = int(n_str)
    except ValueError:
        await send_error(send, HTTPStatus.UNPROCESSABLE_ENTITY, "Parameter 'n' must be an integer")
        return
    
    # Cas limite: nombre négatif
    if n < 0:
        await send_error(send, HTTPStatus.BAD_REQUEST, "Invalid value for n, must be non-negative")
        return
    
    # Cas limite: nombre trop grand
    if n > 1000:
        await send_error(send, HTTPStatus.BAD_REQUEST, "Value too large for n")
        return
    
    result = math.factorial(n)
    await send_json_response(send, {"result": result})


async def handle_fibonacci(scope, receive, send):
    """Обработка GET /fibonacci/5"""
    path_parts = scope["path"].split("/")
    
    # Cas limite: format d'URL incorrect
    if len(path_parts) < 3:
        await send_error(send, HTTPStatus.UNPROCESSABLE_ENTITY, "Invalid URL format")
        return
    
    try:
        n = int(path_parts[2])
    except ValueError:
        await send_error(send, HTTPStatus.UNPROCESSABLE_ENTITY, "Path parameter must be an integer")
        return
    
    # Cas limite: nombre négatif
    if n < 0:
        await send_error(send, HTTPStatus.BAD_REQUEST, "Invalid value for n, must be non-negative")
        return
    
    # Cas limite: nombre trop grand
    if n > 1000:
        await send_error(send, HTTPStatus.BAD_REQUEST, "Value too large for n")
        return
    
    # Расчет Fibonacci
    if n == 0:
        result = 0
    elif n == 1:
        result = 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        result = b
    
    await send_json_response(send, {"result": result})


async def handle_mean(scope, receive, send):
    """Обработка /mean - supporte GET et POST avec différents formats"""
    # Essayer de lire le JSON depuis le body (pour les tests GET avec JSON)
    body = await read_request_body(receive)
    
    has_json_body = False
    numbers = []
    
    if body.strip():
        try:
            data = json.loads(body)
            if isinstance(data, list):
                numbers = [float(x) for x in data]
                has_json_body = True
        except (ValueError, TypeError, json.JSONDecodeError):
            pass  # Ignorer et essayer avec query parameter
    
    # Si pas de JSON body valide, essayer avec query parameter
    if not has_json_body:
        query_params = parse_query_string(scope["query_string"])
        numbers_str = query_params.get("numbers", [""])[0]
        
        if not numbers_str:
            await send_error(send, HTTPStatus.UNPROCESSABLE_ENTITY, "Missing parameter 'numbers' or JSON body")
            return
        
        try:
            numbers = [float(x.strip()) for x in numbers_str.split(",") if x.strip()]
        except ValueError:
            await send_error(send, HTTPStatus.UNPROCESSABLE_ENTITY, "Parameter 'numbers' must be comma-separated floats")
            return
    
    # Validation commune
    if len(numbers) == 0:
        await send_error(send, HTTPStatus.BAD_REQUEST, "Numbers array must not be empty")
        return
    
    # Vérifier les valeurs non numériques
    if any(math.isnan(x) or math.isinf(x) for x in numbers):
        await send_error(send, HTTPStatus.BAD_REQUEST, "Numbers must be finite values")
        return
    
    # Calcul du résultat
    result = sum(numbers) / len(numbers)
    await send_json_response(send, {"result": result})


async def read_request_body(receive) -> str:
    """Чтение полного тела запроса"""
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    return body.decode()


async def send_json_response(send, data: dict):
    """Отправка JSON ответа"""
    response_body = json.dumps(data).encode()
    
    await send({
        "type": "http.response.start",
        "status": HTTPStatus.OK.value,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })
    
    await send({
        "type": "http.response.body",
        "body": response_body,
    })


async def send_error(send, status: HTTPStatus, message: str):
    """Отправка HTTP ошибки"""
    error_data = {"error": message}
    response_body = json.dumps(error_data).encode()
    
    await send({
        "type": "http.response.start",
        "status": status.value,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })
    
    await send({
        "type": "http.response.body",
        "body": response_body,
    })


def parse_query_string(query_string: bytes) -> dict:
    """Парсинг query string параметров"""
    return parse_qs(query_string.decode())


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)