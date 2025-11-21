from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import json

# утилита для ответа
async def _respond(send, status: int, payload: dict[str, Any]):
    body = json.dumps(payload).encode("utf-8")
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", b"application/json"]],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })

def _match_route(path: str) -> str:
    if path == "/factorial":
        return "factorial"
    if path.startswith("/fibonacci"):
        return "fibonacci"
    if path == "/mean":
        return "mean"
    return "not_found"

def fact(n: int) -> int:
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r

def fib(n: int) -> int:
    if n == 0:
        return 0
    elif n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

async def _read_body(receive) -> bytes:
    chunks = []
    while True:
        event = await receive()
        if event["type"] == "http.request":
            if event.get("body"):
                chunks.append(event["body"])
            if not event.get("more_body", False):
                break
        elif event["type"] == "http.disconnect":
            return b""
    return b"".join(chunks)



async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    t = scope["type"]

    # 1) lifespan — нужен TestClient
    if t == "lifespan":
        while True:
            event = await receive()
            et = event["type"]
            if et == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif et == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    # 2) http
    if t != "http":
        return

    method: str = scope["method"]
    path: str = scope["path"]

    route = _match_route(path)

    if route == "not_found":
        await _respond(send, 404, {"detail": "Not Found"})
        return

    allowed = {"GET"}
    if method not in allowed:
        await _respond(send, 405, {"detail": "Method Not Allowed"})
        return

    if route == "factorial":
        qs_bytes = scope.get("query_string", b"")
        qs = parse_qs(qs_bytes.decode("utf-8") if qs_bytes else "", keep_blank_values=True)

        raw = qs.get("n", [None])[0]

        if raw is None or raw == "":
            await _respond(send, 422, {"detail": "Unprocessable Entity"})
            return
        try:
            n = int(raw)
        except ValueError:
            await _respond(send, 422, {"detail": "Unprocessable Entity"})
            return
        if n < 0:
            await _respond(send, 400, {"detail": "Bad Request"})
            return
        await _respond(send, 200, {"result": fact(n)})
        return
    
    if route == "fibonacci":
        parts = path.split("/")
        if len(parts) != 3 or parts[2] == "":
            await _respond(send, 422, {"detail": "Unprocessable Entity"})
            return
        
        raw = parts[2]
        
        try:
            n = int(raw)
        except ValueError:
            await _respond(send, 422, {"detail": "Unprocessable Entity"})
            return
        
        if n < 0:
            await _respond(send, 400, {"detail": "Bad Request"})
            return
        
        await _respond(send, 200, {"result": fib(n)})
        return


    if route == "mean":
        raw = await _read_body(receive)

    if not raw or raw.strip() == b"":
        await _respond(send, 422, {"detail": "Unprocessable Entity"}); 
        return
    try:
        data = json.loads(raw)
    except Exception:
        await _respond(send, 422, {"detail": "Unprocessable Entity"}); return
    
    if data is None or not isinstance(data, list):
        await _respond(send, 422, {"detail": "Unprocessable Entity"}); return
    if len(data) == 0:
        await _respond(send, 400, {"detail": "Bad Request"}); return
    if not all(isinstance(x, (int, float)) for x in data):
        await _respond(send, 400, {"detail": "Bad Request"}); return


    mean = sum(float(x) for x in data) / len(data)
    await _respond(send, 200, {"result": mean}); return


