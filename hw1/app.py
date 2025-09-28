import json
import math
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)


def fibonacci(n: int) -> int:
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)


def mean(numbers: list) -> float:
    return sum(numbers) / len(numbers)


async def send_json_response(send, status_code: int, data: dict):
    await send({
        'type': 'http.response.start',
        'status': status_code,
        'headers': [(b'content-type', b'application/json')],
    })
    await send({
        'type': 'http.response.body',
        'body': json.dumps(data).encode(),
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
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                break

    if scope['type'] != 'http':
        return

    method = scope['method']
    path = scope['path']
    query_string = scope.get('query_string', b'').decode()

    if method != 'GET':
        await send_json_response(send, 404, {})
        return

    if path == '/factorial':
        await handle_factorial(send, query_string)
    elif path.startswith('/fibonacci/'):
        n_str = path[11:] 
        await handle_fibonacci(send, n_str)
    elif path == '/mean':
        await handle_mean(send, receive)
    else:
        await send_json_response(send, 404, {})


async def handle_factorial(send, query_string: str):
    query_params = parse_qs(query_string)

    if 'n' not in query_params:
        await send_json_response(send, 422, {})
        return

    try:
        n = int(query_params['n'][0])
    except (ValueError, IndexError):
        await send_json_response(send, 422, {})
        return

    if n < 0:
        await send_json_response(send, 400, {})
        return

    result = factorial(n)
    await send_json_response(send, 200, {"result": result})


async def handle_fibonacci(send, n_str: str):
    try:
        n = int(n_str)
    except ValueError:
        await send_json_response(send, 422, {})
        return

    if n < 0:
        await send_json_response(send, 400, {})
        return

    result = fibonacci(n)
    await send_json_response(send, 200, {"result": result})


async def handle_mean(send, receive):
    body = b''
    while True:
        message = await receive()
        if message['type'] == 'http.request':
            body += message.get('body', b'')
            if not message.get('more_body', False):
                break

    if not body:
        await send_json_response(send, 422, {})
        return

    try:
        data = json.loads(body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        await send_json_response(send, 422, {})
        return

    if not isinstance(data, list):
        await send_json_response(send, 422, {})
        return

    if len(data) == 0:
        await send_json_response(send, 400, {})
        return

    try:
        result = mean(data)
        await send_json_response(send, 200, {"result": result})
    except (TypeError, ValueError):
        await send_json_response(send, 422, {})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
