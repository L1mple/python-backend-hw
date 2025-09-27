import json
from http import HTTPStatus
from math import factorial
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


def parse_int(value: Any | None) -> int | None:
    try:
        return int(value)  # type: ignore
    except (ValueError, TypeError):
        return None


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
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
                return

    if scope['type'] != 'http':
        return

    path = scope.get('path', '')
    status = HTTPStatus.OK
    body: dict[str, Any] = {}

    if path.startswith('/fibonacci'):
        n = parse_int(path.split('/')[2])

        if n is None:
            status = HTTPStatus.UNPROCESSABLE_ENTITY
        elif n < 0:
            status = HTTPStatus.BAD_REQUEST
        else:
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            body = {'result': a}

    elif path == '/factorial':
        query_string = scope.get('query_string', b'').decode()
        params = {k: v[0] for k, v in parse_qs(query_string).items()}
        n = parse_int(params.get('n'))

        if n is None:
            status = HTTPStatus.UNPROCESSABLE_ENTITY
        elif n < 0:
            status = HTTPStatus.BAD_REQUEST
        else:
            body = {'result': factorial(n)}

    elif path == '/mean':
        request_body = b''

        while True:
            message = await receive()
            if message['type'] == 'http.request':
                request_body += message.get('body', b'')

                if not message.get('more_body', False):
                    break

        data = json.loads(request_body.decode())
        if not isinstance(data, list):
            status = HTTPStatus.UNPROCESSABLE_ENTITY
        elif len(data) == 0:
            status = HTTPStatus.BAD_REQUEST
        elif all(isinstance(x, (int, float)) for x in data):
            body = {'result': sum(data) / len(data)}
        else:
            status = HTTPStatus.UNPROCESSABLE_ENTITY

    else:
        status = HTTPStatus.NOT_FOUND

    body_bytes = json.dumps(body).encode()
    headers = [
        (b'content-type', b'application/json'),
        (b'content-length', str(len(body_bytes)).encode()),
    ]

    await send(
        {
            'type': 'http.response.start',
            'status': status,
            'headers': headers,
        }
    )
    await send(
        {
            'type': 'http.response.body',
            'body': body_bytes,
        }
    )


if __name__ == '__main__':
    import uvicorn

    uvicorn.run('app:application', host='0.0.0.0', port=8000, reload=True)
