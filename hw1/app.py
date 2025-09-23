import math
import json
from typing import Any, Awaitable, Callable, Dict
from urllib.parse import parse_qs

def is_int(n : str) -> bool:
    if n.startswith('-'):
        return n[1:].isnumeric() and not '.' in n
    return n.isnumeric() and not '.' in n

def fibonacci(n : int) -> int:
    if n < 2:
        return n
    prev, current = 0, 1
    for _ in range(2, n+1):
        prev, current = current, current + prev
    return current

async def respond(
    status : int,
    payload : Dict[str, Any],
    send: Callable[[dict[str, Any]], Awaitable[None]]
):
    headers = [(b"content-type", b"application/json; charset=utf-8")]
    body = json.dumps(payload).encode()
    await send({
        "type" : "http.response.start",
        "status" : status,
        "headers" : headers
    })
    await send({
        "type" : "http.response.body",
        "body" : body
    })

async def fibonacci_handler(
    scope: dict[str, Any],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    n = scope['path'].strip('/').split('/')[1]
    if not is_int(n):
        return await respond(422, {"error" : "Argument must be non-negative integer"}, send)
    n = int(n)
    if n < 0:
        return await respond(400, {"error" : "Argument must be non-negative integer"}, send)
    res = fibonacci(n)
    return await respond(200, {"result" : res}, send)

async def factorial_handler(
    scope: dict[str, Any],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    args = parse_qs(scope['query_string'])
    if len(args) != 1 or b'n' not in args:
        return await respond(422, {"error" : "Invalid query"}, send)
    n = args[b'n'][0].decode('utf-8')
    if not is_int(n):
        return await respond(422, {"error" : "Argument must be non-negative integer"}, send)
    n = int(n)
    if n < 0:
        return await respond(400, {"error" : "Argument must be non-negative integer"}, send)
    res = math.factorial(n)
    return await respond(200, {"result" : res}, send)

async def mean_handler(
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    body = b""
    more_body = True
    while more_body:
        event = await receive()
        if event['type'] == "http.request":
            body += event.get('body', b'')
            more_body = event.get('more_body', False)
        else:
            more_body = False

    try:
        array = list(json.loads(body.decode()))
    except json.JSONDecodeError:
        return await respond(422, {"error" : "Invalid JSON body"}, send)
    except TypeError:
        return await respond(422, {"error" : "Got None as list"}, send)

    try:
        result = sum(array)/len(array)
    except ZeroDivisionError:
        return await respond(400, {"error" : "List is empty"}, send)

    return await respond(200, {"result" : result}, send)


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    path = scope.get('path', '/')
    method = scope.get('method', 'GET')

    if path.startswith("/fibonacci") and method == "GET":
        return await fibonacci_handler(scope, send)
    elif path.startswith("/factorial") and method == "GET":
        return await factorial_handler(scope, send)
    elif path.startswith("/mean") and method == "GET":
        return await mean_handler(receive, send)

    return await respond(404, {"error" : "Not found"}, send)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
