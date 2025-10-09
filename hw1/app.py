import math
import statistics
import json
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
from http import HTTPStatus


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    # --- lifespan поддержка для тест-клиента ---
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
        return

    if scope['type'] != 'http':
        return

    path = scope.get('path', '/')
    method = scope.get('method', 'GET').upper()
    query_string = scope.get('query_string', b'').decode()
    params = parse_qs(query_string)

    async def send_response(status: int, data: dict):
        body = json.dumps(data).encode('utf-8')
        headers = [(b'content-type', b'application/json')]
        await send({'type': 'http.response.start', 'status': status, 'headers': headers})
        await send({'type': 'http.response.body', 'body': body})

    # --- поддерживаем только GET ---
    if method != 'GET':
        await send_response(HTTPStatus.NOT_FOUND, {'detail': 'Not Found'})
        return

    # --- factorial ---
    if path == '/factorial':
        if 'n' not in params or params['n'][0] == '':
            await send_response(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Missing n'})
            return
        try:
            n = int(params['n'][0])
        except Exception:
            await send_response(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'n must be int'})
            return

        if n < 0 or n > 100:
            await send_response(HTTPStatus.BAD_REQUEST, {'detail': 'n must be between 0 and 100'})
            return

        result = math.factorial(n)
        await send_response(HTTPStatus.OK, {'result': result})
        return

    # --- fibonacci ---
    elif path.startswith('/fibonacci'):
        parts = path.split('/')
        if len(parts) != 3 or parts[2] == '':
            await send_response(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Invalid path'})
            return
        try:
            n = int(parts[2])
        except Exception:
            await send_response(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'n must be int'})
            return

        if n < 0 or n > 100:
            await send_response(HTTPStatus.BAD_REQUEST, {'detail': 'n must be between 0 and 100'})
            return

        a, b = 0, 1
        seq = []
        for _ in range(n):
            seq.append(a)
            a, b = b, a + b
        await send_response(HTTPStatus.OK, {'result': seq})
        return

    # --- mean ---
    elif path == '/mean':
        event = await receive()
        body = b''
        if event.get('type') == 'http.request':
            body = event.get('body', b'') or b''

        if not body:
            await send_response(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Missing JSON body'})
            return

        try:
            data = json.loads(body)
        except Exception:
            await send_response(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Invalid JSON'})
            return

        if not isinstance(data, list):
            await send_response(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Body must be a list'})
            return

        if len(data) == 0:
            await send_response(HTTPStatus.BAD_REQUEST, {'detail': 'Empty list'})
            return

        try:
            numbers = [float(x) for x in data]
            result = statistics.mean(numbers)
            await send_response(HTTPStatus.OK, {'result': result})
            return
        except Exception:
            await send_response(HTTPStatus.UNPROCESSABLE_ENTITY, {'detail': 'Invalid numbers'})
            return

    # --- not found ---
    await send_response(HTTPStatus.NOT_FOUND, {'detail': 'Not Found'})


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('app:application', host='0.0.0.0', port=8000, reload=True)
