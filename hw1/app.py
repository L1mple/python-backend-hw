from typing import Any, Awaitable, Callable
import json
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

    def factorial(n: int) -> int:
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0 or n == 1:
            return 1
        return n * factorial(n - 1)

    def fibonacci(n: int) -> int:
        if n < 0:
            raise ValueError("n must be non-negative")
        if n == 0:
            return 0
        if n == 1:
            return 1
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b

    def mean(values: list[float]) -> float:
        if not values:
            raise ValueError("values cannot be empty")
        return sum(values) / len(values)

    async def send_response(status: int, body: dict = None):
        await send({
            'type': 'http.response.start',
            'status': status,
            'headers': [[b'content-type', b'application/json']],
        })

        response_body = json.dumps(body or {}).encode('utf-8')
        await send({
            'type': 'http.response.body',
            'body': response_body,
        })

    # Main application logic
    if scope['type'] != 'http':
        await send_response(404)
        return

    method = scope['method']
    path = scope['path']

    if method != 'GET':
        await send_response(404)
        return

    if path == '/factorial':
        query_string = scope.get('query_string', b'').decode('utf-8')
        params = parse_qs(query_string)

        if 'n' not in params:
            await send_response(422)
            return

        try:
            n_str = params['n'][0]
            if not n_str.isdigit() and not (n_str.startswith('-') and n_str[1:].isdigit()):
                await send_response(422)
                return
            n = int(n_str)
        except (ValueError, IndexError):
            await send_response(422)
            return

        if n < 0:
            await send_response(400)
            return

        try:
            result = factorial(n)
            await send_response(200, {'result': result})
        except Exception:
            await send_response(400)

    elif path.startswith('/fibonacci/'):
        try:
            n_str = path[11:]  # Remove '/fibonacci/'
            if not n_str.isdigit() and not (n_str.startswith('-') and n_str[1:].isdigit()):
                await send_response(422)
                return
            n = int(n_str)
        except ValueError:
            await send_response(422)
            return

        if n < 0:
            await send_response(400)
            return

        try:
            result = fibonacci(n)
            await send_response(200, {'result': result})
        except Exception:
            await send_response(400)

    elif path == '/mean':
        body = b''
        while True:
            message = await receive()
            if message['type'] == 'http.request':
                body += message.get('body', b'')
                if not message.get('more_body', False):
                    break

        if not body:
            await send_response(422)
            return

        try:
            data = json.loads(body.decode('utf-8'))
        except json.JSONDecodeError:
            await send_response(422)
            return

        if not isinstance(data, list):
            await send_response(422)
            return

        if not data:
            await send_response(400)
            return

        try:
            float_values = [float(x) for x in data]
        except (TypeError, ValueError):
            await send_response(422)
            return

        try:
            result = mean(float_values)
            await send_response(200, {'result': result})
        except Exception:
            await send_response(400)

    else:
        await send_response(404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
