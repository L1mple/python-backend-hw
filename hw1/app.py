import json
import math
from http import HTTPStatus
from typing import Any, Awaitable, Callable

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

    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    if scope['type'] == 'http':
        path = scope['path'].split("/")[1:]
        
        match path[0]:
            case "fibonacci":
                await fibonacci(
                    scope = scope,
                    send = send,
                )
                
            case "factorial":
                await factorial(
                    scope = scope,
                    send = send,
                )
                
            case "mean":
                await mean(
                    receive=receive,
                    send = send,
                )
            
            case _:
                await send_response(
                    send = send,
                    data = {"error": "Not available"},
                    status = HTTPStatus.NOT_FOUND,
                )
       
async def fibonacci(
    scope: dict[str, Any],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    path = scope['path'].split("/")[1:]
    
    try:
        value = int(path[1])
    except ValueError:
        return await send_response(
            send = send,
            data = { "error": "path parameter is not an integer" },
            status = HTTPStatus.UNPROCESSABLE_ENTITY,
        )

    if value < 0:
        return await send_response(
            send = send,
            data = { "error": "path parameter can't be negative" },
            status = HTTPStatus.BAD_REQUEST,
        )
    else:
        return await send_response(
            send = send,
            data = { "result": _fibonacci(value) },
            status = HTTPStatus.OK
        )
    
def _fibonacci(n: int) -> int:
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b 
    
async def factorial(
    scope: dict[str, Any],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    query_params: dict[str, Any] = await read_query_params(scope)

    if "n" not in query_params:
        return await send_response(
            send = send,
            data = { "error": "no query param with name \"n\""},
            status = HTTPStatus.UNPROCESSABLE_ENTITY,
        )
        
    try:
        n = int(query_params['n'])
    except:
        return await send_response(
            send = send,
            data = { "error": "invalid value of param \"n\""},
            status = HTTPStatus.UNPROCESSABLE_ENTITY,
        )
        
    try:
        return await send_response(
            send = send,
            data = { "result": math.factorial(n) },
            status = HTTPStatus.OK,
        )
    except ValueError:
        return await send_response(
            send = send,
            data = { "error": "value of \"n\" is negative"},
            status = HTTPStatus.BAD_REQUEST,
        )
    
async def mean(
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
): 
    try:
        body = await read_body(receive=receive)
        numbers_data = json.loads(body)
    except json.JSONDecodeError:
        return await send_response(
            send = send,
            data = {"error": "Invalid JSON"},
            status = HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    
    if not isinstance(numbers_data, list):
        return await send_response(
            send = send,
            data = { "error": "numbers is not a list"},
            status = HTTPStatus.UNPROCESSABLE_ENTITY,
        )
    elif len(numbers_data) == 0:
        return await send_response(
            send = send,
            data = { "error": "numbers is empty"},
            status = HTTPStatus.BAD_REQUEST,
        )
    else:
        mean = sum(numbers_data) / len(numbers_data)
        return await send_response(
            send = send,
            data = { "result": mean },
            status = HTTPStatus.OK
        )
        
        
    
async def read_body(
    receive: Callable[[], Awaitable[dict[str, Any]]],
):
    body = b''
    more_body = True

    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)

    return body.decode('utf-8')
        
async def read_query_params(
    scope: dict[str, Any],
) -> dict[str, Any]:
    query_string: str | None = scope.get("query_string", b"").decode()
    params: dict[str, Any] = {}
    if query_string:
        for param in query_string.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key] = value
                
    return params

async def send_response(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    data: dict[str, Any],
    status: HTTPStatus,
):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", b"application/json"]]
    })
    await send({
        "type": "http.response.body",
        "body": json.dumps(data).encode(),
    })
    return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
