from typing import Any, Awaitable, Callable
import math
import json 
from urllib.parse import parse_qs

def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def mean(nums):
    return sum(nums) / len(nums)

async def send_response(send, status, data):
    body = json.dumps(data).encode()
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": body})

async def factorial_endpoint(send, query_string):
    q = parse_qs(query_string)
    nums = q.get("n")
    if not nums:
        await send_response(send, 422, {})
        return

    try:
        n = int(nums[0])
    except ValueError:
        await send_response(send, 422, {})
        return

    if n < 0:
        await send_response(send, 400, {})
        return

    await send_response(send, 200, {"result": math.factorial(n)})

async def fibonacci_endpoint(send, n_str):
    try:
        n = int(n_str)
    except ValueError:
        await send_response(send, 422, {})
        return
    
    if n < 0:
        await send_response(send, 400, {"error": "n must be >= 0"})
        return
    await send_response(send, 200, {"result": fibonacci(n)})
    
async def mean_endpoint(send, receive):
    body = b""
    while True:
        message = await receive()
        if message["type"] == "http.request":
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break
    if not body:
        await send_response(send, 422, {})
        return
    try:
        data = json.loads(body.decode())
    except (json.JSONDecodeError, UnicodeDecodeError):
        await send_response(send, 422, {})
        return
    if not isinstance(data, list):
        await send_response(send, 422, {})
        return
    if len(data) == 0:
        await send_response(send, 400, {})
        return
    try:
        await send_response(send, 200, {"result": mean(data)})
    except (TypeError, ValueError):
        await send_response(send, 422, {})
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
    # TODO: Ваша реализация здесь
    
    if scope['type'] == 'lifespan':
            while True:
                message = await receive()
                if message['type'] == 'lifespan.startup':
                    await send({'type': 'lifespan.startup.complete'})
                elif message['type'] == 'lifespan.shutdown':
                    await send({'type': 'lifespan.shutdown.complete'})
                    break
            return
    if scope['type'] != 'http':
        return
    method = scope['method']
    path = scope['path']
    query_string = scope.get('query_string', b'').decode()

    if method != 'GET':
        await send_response(send, 404, {"error": "Not found"})
        return

    if path == '/factorial':
        await factorial_endpoint(send, query_string)
    elif path.startswith('/fibonacci/'):
        n_str = path[len('/fibonacci/'):]
        await fibonacci_endpoint(send, n_str)
    elif path == '/mean':
        await mean_endpoint(send, receive)
    else:
        await send_response(send, 404, {"error": "Not found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
