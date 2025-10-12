import json
from math import factorial
from typing import Any, Awaitable, Callable
from http import HTTPStatus
from urllib.parse import parse_qsl


def fibonacci(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def mean(array: list[int | float]) -> float:
    return sum(array) / len(array)


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
    async def send_json_response(status_code: int, content: dict):
        body = json.dumps(content).encode('utf-8')
        await send({
            'type': 'http.response.start',
            'status': status_code,
            'headers': [(b'Content-Type', b'application/json')],
        })
        await send({
            'type': 'http.response.body',
            'body': body,
        })

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

    path_parts = scope['path'].strip('/').split('/')

    if path_parts and path_parts[0]:
        scenario = path_parts[0]
    else:
        scenario = ''

    if scenario == 'factorial':
        query_params = dict(parse_qsl(scope['query_string']))
        n_str = query_params.get(b'n', b'').decode('utf-8')

        if not n_str:
            return await send_json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "There is no n"}
            )

        try:
            n = int(n_str)
        except (ValueError, TypeError):
            return await send_json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "n must be an integer."}
            )

        if n < 0:
            return await send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": "n must be a positive integer."}
            )

        result = factorial(n)
        return await send_json_response(HTTPStatus.OK, {"result": result})

    elif scenario == 'fibonacci':
        if len(path_parts) != 2:
            return await send_json_response(
                HTTPStatus.NOT_FOUND,
                {"error": "Not Found"}
            )

        n_str = path_parts[1]
        try:
            n = int(n_str)
        except (ValueError, TypeError):
            return await send_json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "n must be an integer."}
            )

        if n < 0:
            return await send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": "n must be a positive integer."}
            )

        result = fibonacci(n)
        return await send_json_response(HTTPStatus.OK, {"result": result})

    elif scenario == 'mean':
        body = b''
        more_body = True
        while more_body:
            message = await receive()
            body += message.get('body', b'')
            more_body = message.get('more_body', False)

        if not body:
            return await send_json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "Request body is empty."}
            )

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return await send_json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "Invalid JSON"}
            )

        if not isinstance(data, list):
            return await send_json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "Request body must be a JSON array."}
            )

        if not data:
            return await send_json_response(
                HTTPStatus.BAD_REQUEST,
                {"error": "list must not be empty."}
            )

        if not all(isinstance(x, (int, float)) for x in data):
            return await send_json_response(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "All elements in the list must be numbers."}
            )

        result = mean(data)
        return await send_json_response(HTTPStatus.OK, {"result": result})

    else:
        return await send_json_response(HTTPStatus.NOT_FOUND, {"error": "Not Found"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)