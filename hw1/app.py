from http import HTTPStatus
from typing import Any, Awaitable, Callable
import json
from urllib.parse import parse_qs
import math

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
    if scope['type'] == 'http':
        method = scope['method']
        path = scope['path']
        # Факториал
        if method == 'GET' and path == '/factorial':
            await handle_factorial(scope, send)

        # Фибоначчи
        elif method == 'GET' and path.startswith('/fibonacci'):
            await handle_fibonacci(scope, send)

        # Среднее значение
        elif method == 'GET' and path == '/mean':
            await handle_mean(scope, receive, send)

        # Все остальные пути - 404
        else:
            await send_json_response(
                send,
                HTTPStatus.NOT_FOUND,
                {'error': 'Not found'}
            )

    elif scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return

def get_query_params(scope):
    query_string = scope.get('query_string', b'').decode()
    query_params = parse_qs(query_string)
    return {k: v[0] if v else '' for k, v in query_params.items()}


async def handle_factorial(scope, send):
    query_params = get_query_params(scope)
    n_str = query_params.get('n', '')

    if not n_str:
        await send_json_response(
            send,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {'error': 'Parameter n is required'}
        )
        return
    try:
        n = int(n_str)
    except ValueError:
        await send_json_response(
            send,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {'error': 'Parameter n must be an integer'}
        )
        return
    if n < 0:
        await send_json_response(
            send,
            HTTPStatus.BAD_REQUEST,
            {'error': 'Parameter n must be non-negative'}
        )
        return

    result = math.factorial(n)
    await send_json_response(
        send,
        HTTPStatus.OK,
        {'result': result}
    )


async def handle_fibonacci(scope, send):
    path = scope['path']

    parts = path.split('/')
    if len(parts) != 3:
        await send_json_response(
            send,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {'error': 'Invalid path format'}
        )
        return

    try:
        n_str = parts[2]
        n = int(n_str)
    except ValueError:
        await send_json_response(
            send,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {'error': 'Parameter must be an integer'}
        )
        return

    if n < 0:
        await send_json_response(
            send,
            HTTPStatus.BAD_REQUEST,
            {'error': 'Parameter must be non-negative'}
        )
        return

    if n == 0:
        result = 0
    elif n == 1:
        result = 1
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        result = b

    await send_json_response(
        send,
        HTTPStatus.OK,
        {'result': result}
    )


async def handle_mean(scope, receive, send):
    body = await read_body(receive)

    if not body:
        await send_json_response(
            send,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {'error': 'JSON body is required'}
        )
        return

    try:
        data = json.loads(body.decode())
    except json.JSONDecodeError:
        await send_json_response(
            send,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {'error': 'Invalid JSON'}
        )
        return

    if data is None:
        await send_json_response(
            send,
            HTTPStatus.UNPROCESSABLE_ENTITY,
            {'error': 'JSON body cannot be null'}
        )
        return

    if not isinstance(data, list):
        await send_json_response(
            send,
            HTTPStatus.BAD_REQUEST,
            {'error': 'Expected a list of numbers'}
        )
        return

    if not data:
        await send_json_response(
            send,
            HTTPStatus.BAD_REQUEST,
            {'error': 'List cannot be empty'}
        )
        return

    try:
        numbers = []
        for item in data:
            if isinstance(item, (int, float)):
                numbers.append(float(item))
            else:
                raise ValueError("Not a number")
    except (ValueError, TypeError):
        await send_json_response(
            send,
            HTTPStatus.BAD_REQUEST,
            {'error': 'All elements must be numbers'}
        )
        return

    mean = sum(numbers) / len(numbers)
    await send_json_response(
        send,
        HTTPStatus.OK,
        {'result': mean}
    )


async def send_json_response(send, status, data):
    body = json.dumps(data).encode('utf-8')
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [
            [b'content-type', b'application/json'],
            [b'content-length', str(len(body)).encode()],
        ],
    })
    await send({
        'type': 'http.response.body',
        'body': body,
    })

async def read_body(receive):
    body = b''
    more_body = True
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    return body

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
