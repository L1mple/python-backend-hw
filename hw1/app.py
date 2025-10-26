from typing import Any, Awaitable, Callable
import json


def response_start(body, code):
    return {
        'type': 'http.response.start',
        'status': code,
        'headers': [
            (b'content-type', b'application/json'),
            (b'content-length', str(len(body)).encode())
        ]
    }


def response_body(body):
    return {
        'type': 'http.response.body',
        'body': body.encode(),
    }


def calculate_factorial(n):
    return 1 if n < 2 else calculate_factorial(n - 1) * n


def calculate_fibonacci(n):
    return n if n in (0, 1) else calculate_fibonacci(n - 1) + calculate_fibonacci(n - 2)


def calculate_mean(numbers):
    return sum(numbers) / len(numbers)


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

    elif scope['type'] == 'http':
        body = ''
        code = 200
        if scope['path'] == '/factorial':
            if scope['query_string'].startswith(b"n="):
                key, value = scope['query_string'].decode().split('=')
                try:
                    n = int(value)
                    if n < 0:
                        code = 400
                    else:
                        code = 200
                        body = json.dumps({"result": calculate_factorial(n)})
                except ValueError:
                    code = 422
            else:
                code = 422

        elif scope['path'].startswith('/fibonacci/'):
            try:
                n = int(scope['path'][len('/fibonacci/'):])
                if n < 0:
                    code = 400
                else:
                    code = 200
                    body = json.dumps({"result": calculate_fibonacci(n)})
            except ValueError:
                code = 422

        elif scope['path'] == '/mean':
            message = await receive()
            request_body = json.loads(message['body'])
            try:
                request_body = list(request_body)
                if len(request_body) == 0:
                    code = 400
                else:
                    body = json.dumps({"result": calculate_mean(request_body)})
            except TypeError:
                code = 422

        else:
            code = 404
        await send(response_start(body, code))
        await send(response_body(body))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
