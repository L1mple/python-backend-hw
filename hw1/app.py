import math
import json
from http import HTTPStatus
from typing import Any, Awaitable, Callable

async def read_body(receive):
    body = b''
    more_body = True
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    return body


def parse_query_string(scope: dict[str, Any]):
    result = {}
    query_string = scope.get('query_string').decode()
    if len(query_string) == 0:
        return result
    for entry in query_string.split('&'):
        key, value = entry.split('=')
        result[key] = value
    return result


def not_found_response(value = ""):
    return {
        'value': str(value),
        'code': HTTPStatus.NOT_FOUND
    }

def bad_request_response(value = ""):
    return {
        'value': str(value),
        'code': HTTPStatus.BAD_REQUEST
    }

def unprocessable_content_response(value = ""):
    return {
        'value': str(value),
        'code': HTTPStatus.UNPROCESSABLE_CONTENT
    }

def ok_response(value = ""):
    return {
        'value': str(value),
        'code': HTTPStatus.OK
    }


def get_factorial(query_params: dict[str, Any], path_parameters: list[str], body: bytes) -> dict[str, Any]:
    n = int(query_params.get('n'))
    if n < 0:
        return bad_request_response("Invalid value for n, must be a non-negative")
    result = math.factorial(n)
    return ok_response(result)


def get_fibonacci(query_params: dict[str, Any], path_parameters: list[str], body: bytes) -> dict[str, Any]:
    n = int(path_parameters[0])
    if n < 0:
        return bad_request_response("Invalid value for n, must be a non-negative")
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return ok_response(a)


def get_mean(query_params: dict[str, Any], path_parameters: list[str], body: bytes) -> dict[str, Any]:
    data = json.loads(body.decode())
    if len(data) == 0:
        return bad_request_response("Invalid value for body, must be non-empty array of floats")
    result = sum(data) / len(data)
    return ok_response(result)


def route_request(scope: dict[str, Any]) -> Callable:
    method = scope.get('method')
    path = scope.get('path')

    function = None
    routing_params = []

    if method == "GET":
        if path.startswith("/factorial"):
            function = get_factorial
            routing_params = path[10:].split("/")
        elif path.startswith("/fibonacci"): 
            function = get_fibonacci
            routing_params = path[11:].split("/")
        elif path.startswith("/mean"): 
            function = get_mean
            routing_params = path[6:].split("/")
            
    return [function, routing_params]
    

async def handle_http(scope: dict[str, Any], receive: Callable, send: Callable):

    function, path_parameters = route_request(scope)
    if function is None:
        response = not_found_response()

    else:
        try:
            body = await read_body(receive)
            query_params = parse_query_string(scope)
            response = function(query_params, path_parameters, body)
        except Exception:
            response = unprocessable_content_response()

    code = response['code']
    body = json.dumps({"result": response['value']})
    await send({
        'type': 'http.response.start',
        'status': code,
        'headers': [
            [b'content-type', b'text/plain'],
        ]
    })
    await send({
        'type': 'http.response.body',
        'body': body.encode()
    })


async def handle_lifespan(scope: dict[str, Any], receive: Callable, send: Callable):
    while True:
        message = await receive()
        if message['type'] == 'lifespan.startup':
            await send({'type': 'lifespan.startup.complete'})
        elif message['type'] == 'lifespan.shutdown':
            await send({'type': 'lifespan.shutdown.complete'})
            return


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
    scope_type = scope['type']
    if scope_type == 'lifespan':
        await handle_lifespan(scope, receive, send)
    elif scope_type == 'http':
        await handle_http(scope, receive, send)
    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
