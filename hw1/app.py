from typing import Any, Awaitable, Callable
import json
import math
from urllib.parse import parse_qs

async def respond(send, status: int, body: dict[str, Any]):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": json.dumps(body).encode()})

async def read_http_body(receive) -> bytes:
    chunks: list[bytes] = []
    more = True
    while more:
        message = await receive()
        if message["type"] != "http.request":
            continue
        chunks.append(message.get("body", b""))
        more = message.get("more_body", False)
    return b"".join(chunks)

def parse_query(scope) -> dict[str, list[str]]:
    return parse_qs(scope.get("query_string", b"").decode())

async def handle_fibonacci(method: str, path: str, send):
    if method != "GET":
        return await respond(send, 422, {"error": "Unsupported method"})
    param = path[len("/fibonacci/") :]
    if not param:
        return await respond(send, 422, {"error": "Invalid n"})
    try:
        n = int(param)
    except ValueError:
        return await respond(send, 422, {"error": "Invalid n"})
    if n < 0:
        return await respond(send, 400, {"error": "n must be non-negative"})
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return await respond(send, 200, {"result": a})

async def handle_factorial(method: str, query: dict[str, list[str]], send):
    if method != "GET":
        return await respond(send, 422, {"error": "Unsupported method"})
    raw = query.get("n")
    if not raw or raw[0] == "":
        return await respond(send, 422, {"error": "Invalid n"})
    try:
        n = int(raw[0])
    except ValueError:
        return await respond(send, 422, {"error": "Invalid n"})
    if n < 0:
        return await respond(send, 400, {"error": "n must be non-negative"})
    return await respond(send, 200, {"result": math.factorial(n)})

async def handle_mean(method: str, query: dict[str, list[str]], receive, send):
    if method != "GET":
        return await respond(send, 422, {"error": "Unsupported method"})
    body = await read_http_body(receive)

    if body:
        try:
            data = json.loads(body.decode() or "null")
        except json.JSONDecodeError:
            return await respond(send, 422, {"error": "Invalid JSON body"})
        if not isinstance(data, list):
            return await respond(send, 422, {"error": "Invalid JSON body"})
        if len(data) == 0:
            return await respond(send, 400, {"error": "numbers must be non-empty list"})
        nums: list[float] = []
        for v in data:
            if isinstance(v, (int, float)):
                nums.append(float(v))
            else:
                return await respond(send, 422, {"error": "All items must be numbers"})
        return await respond(send, 200, {"result": sum(nums) / len(nums)})

    numbers_param = query.get("numbers", [None])[0]
    if numbers_param is None:
        return await respond(send, 422, {"error": "Invalid JSON body"})
    parts = [p.strip() for p in numbers_param.split(",") if p.strip()]
    if not parts:
        return await respond(send, 400, {"error": "numbers must be non-empty list"})
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return await respond(send, 422, {"error": "All items must be numbers"})
    return await respond(send, 200, {"result": sum(nums) / len(nums)})

async def handle_lifespan(receive, send):
    while True:
        msg = await receive()
        t = msg.get("type")
        if t == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif t == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
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
    if scope["type"] == "lifespan":
        return await handle_lifespan(receive, send)
    if scope["type"] != "http":
        return

    method = scope["method"]
    path = scope["path"]
    query = parse_query(scope)

    if path.startswith("/fibonacci/"):
        return await handle_fibonacci(method, path, send)
    if path == "/factorial":
        return await handle_factorial(method, query, send)
    if path == "/mean":
        return await handle_mean(method, query, receive, send)

    return await respond(send, 404, {"error": "Not found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
