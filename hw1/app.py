from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import json
import math
import re


HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_NOT_FOUND = 404
HTTP_UNPROCESSABLE_ENTITY = 422


def fibonacci(n: int) -> int:
    if n == 0:
        return 0
    elif n == 1:
        return 1

    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def factorial(n: int) -> int:
    return math.factorial(n)


def mean(numbers: list[int | float]) -> float:
    if not numbers:
        raise ValueError('Empty list')
    return sum(numbers) / len(numbers)


async def read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    body_parts = []
    while True:
        message = await receive()
        if message['type'] != 'http.request':
            continue
        
        body_parts.append(message.get('body', b''))
        if not message.get('more_body', False):
            break

    return b''.join(body_parts)


async def send_response(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    body: dict[str, Any] | None = None,
):
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [[b"content-type", b"application/json"]],
    })

    response_body = json.dumps(body if body else {}).encode('utf-8')
    await send({
        'type': 'http.response.body',
        'body': response_body,
    })


async def handle_lifespan(
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    while True:
        message = await receive()
        if message['type'] == 'lifespan.startup':
            await send({'type': 'lifespan.startup.complete'})
        elif message['type'] == 'lifespan.shutdown':
            await send({'type': 'lifespan.shutdown.complete'})
            return


async def handle_fibonacci(
    path: str,
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    match = re.match(r'^/fibonacci/(.+)$', path)
    if not match:
        await send_response(send, HTTP_NOT_FOUND)
        return

    try:
        n = int(match.group(1))
        if n < 0:
            await send_response(send, HTTP_BAD_REQUEST)
            return

        result = fibonacci(n)
        await send_response(send, HTTP_OK, {'result': result})
    except ValueError:
        await send_response(send, HTTP_UNPROCESSABLE_ENTITY)


async def handle_factorial(
    query_string: bytes,
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    if not query_string:
        await send_response(send, HTTP_UNPROCESSABLE_ENTITY)
        return

    params = parse_qs(query_string.decode('utf-8'))

    if 'n' not in params or len(params['n']) != 1:
        await send_response(send, HTTP_UNPROCESSABLE_ENTITY)
        return

    try:
        n = int(params['n'][0])
        if n < 0:
            await send_response(send, HTTP_BAD_REQUEST)
            return

        result = factorial(n)
        await send_response(send, HTTP_OK, {'result': result})
    except ValueError:
        await send_response(send, HTTP_UNPROCESSABLE_ENTITY)


async def handle_mean(
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    body_bytes = await read_body(receive)

    if not body_bytes:
        await send_response(send, HTTP_UNPROCESSABLE_ENTITY)
        return

    try:
        data = json.loads(body_bytes.decode('utf-8'))

        if not isinstance(data, list):
            await send_response(send, HTTP_UNPROCESSABLE_ENTITY)
            return

        if len(data) == 0:
            await send_response(send, HTTP_BAD_REQUEST)
            return

        if not all(isinstance(x, (int, float)) for x in data):
            await send_response(send, HTTP_UNPROCESSABLE_ENTITY)
            return

        result = mean(data)
        await send_response(send, HTTP_OK, {'result': result})
    except (json.JSONDecodeError, ValueError):
        await send_response(send, HTTP_UNPROCESSABLE_ENTITY)


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    '''
    Args:
        scope: Словарь с информацией о запросе
        receive: Корутина для получения сообщений от клиента
        send: Корутина для отправки сообщений клиенту
    '''
    if scope['type'] == 'lifespan':
        await handle_lifespan(receive, send)
        return

    if scope['type'] != 'http':
        return

    method = scope['method']
    path = scope['path']

    if method != 'GET':
        await send_response(send, HTTP_NOT_FOUND)
        return

    if path.startswith('/fibonacci/'):
        await handle_fibonacci(path, send)
    elif path == '/factorial':
        query_string = scope.get('query_string', b'')
        await handle_factorial(query_string, send)
    elif path == '/mean':
        await handle_mean(receive, send)
    else:
        await send_response(send, HTTP_NOT_FOUND)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('app:application', host='0.0.0.0', port=8000, reload=True)
