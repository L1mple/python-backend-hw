from typing import Any, Awaitable, Callable
from http import HTTPStatus
from urllib.parse import parse_qs
from funcs import NotOK, fibonacci, factorial, mean
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
    if 'path' not in scope:
        await NotOK(send, HTTPStatus.NOT_FOUND, 'Not found')
        return

    if scope['path'].startswith('/fibonacci/'):
        try:
            n = int(scope['path'][11:])
        except ValueError:
            await NotOK(send, HTTPStatus.UNPROCESSABLE_ENTITY, 'Unprocessable Entity')
            return
        if n < 0:
            await NotOK(send, HTTPStatus.BAD_REQUEST, 'Bad request')
            return
        await fibonacci(n, send)
        return

    elif scope['path'].startswith('/factorial'):
        params = parse_qs(scope.get('query_string', b'').decode())
        try:
            n_str = params['n'][0]
        except (KeyError, IndexError):
            await NotOK(send, HTTPStatus.UNPROCESSABLE_ENTITY, 'Unprocessable Entity')
            return
        try:
            n = int(n_str)
        except ValueError:
            await NotOK(send, HTTPStatus.UNPROCESSABLE_ENTITY, 'Unprocessable Entity')
            return
        if n < 0:
            await NotOK(send, HTTPStatus.BAD_REQUEST, 'Bad request')
            return
        await factorial(n, send)
        return

    elif scope['path'].startswith('/mean'):
        message = await receive()
        body = message.get('body').decode()
        data = json.loads(body)
        if not isinstance(data, list):
            await NotOK(send, HTTPStatus.UNPROCESSABLE_ENTITY, 'Unprocessable Entity')
            return
        if not data:
            await NotOK(send, HTTPStatus.BAD_REQUEST, 'Bad request')
            return
        nums = list(map(float, data))
        await mean(nums, send)
        return

    else:
        await NotOK(send, HTTPStatus.NOT_FOUND, 'Not found')


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
