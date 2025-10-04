from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import math
import json

async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    elif scope["type"] == "http":
        path = scope["path"]
        method = scope["method"]

        if path == "/factorial" and method == "GET":
            await handle_factorial(scope, send)
        elif path.startswith("/fibonacci/") and method == "GET":
            await handle_fibonacci(scope, send)
        elif path == "/mean" and method == "GET":
            await handle_mean(receive, send)
        else:
            await send_error(send, 404, "Not Found")

async def handle_factorial(scope, send):
    qs = parse_qs(scope["query_string"].decode("utf-8"))
    
    if "n" not in qs:
        await send_error(send, 422, "Missing parameter 'n'")
        return

    n_str = qs["n"][0]

    try:
        n = int(n_str)
    except (ValueError, TypeError):
        await send_error(send, 422, "Parameter 'n' must be an integer")
        return

    if n < 0:
        await send_error(send, 400, "Factorial is not defined for negative numbers")
        return
    
    
    result = math.factorial(n)
    await send_json_response(send, 200, {"result": result})

async def handle_fibonacci(scope, send):
    path_parts = scope["path"].strip("/").split("/")

    if len(path_parts) != 2:
        await send_error(send, 422, "Invalid path format. Use /fibonacci/<number>")
        return
    
    n_str = path_parts[1]

    try:
        n = int(n_str)
    except ValueError:
        await send_error(send, 422, "Parameter must be an integer")
        return

    if n < 0:
        await send_error(send, 400, "Fibonacci is not defined for negative numbers")
        return
    
    if n <= 1:
        await send_json_response(send, 200, {"result": n})
        return

    a, b = 0, 1
    for _ in range(2, n):
        a, b = b, a + b
    
    await send_json_response(send, 200, {"result": b})

async def handle_mean(receive, send):
    body = await get_request_body(receive)
    
    if not body:
        await send_error(send, 422, "Request body is missing")
        return

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        await send_error(send, 422, "Invalid JSON in request body")
        return
    
    if not isinstance(data, list):
        await send_error(send, 422, "Request body must be a JSON array")
        return

    if not data:
        await send_error(send, 400, "Cannot calculate mean of an empty list")
        return
        
    if not all(isinstance(x, (int, float)) for x in data):
        await send_error(send, 422, "All elements in the array must be numbers")
        return

    result = sum(data) / len(data)
    await send_json_response(send, 200, {"result": result})


async def get_request_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    body = b''
    more_body = True
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    return body

async def send_json_response(send, status_code, data):
    body = json.dumps(data).encode("utf-8")
    await send_response(send, status_code, body, "application/json")

async def send_error(send, status_code, message):
    await send_json_response(send, status_code, {"error": message})

async def send_response(send, status_code, body, content_type):
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": [
            [b"content-type", content_type.encode("utf-8")],
            [b"content-length", str(len(body)).encode("utf-8")],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
