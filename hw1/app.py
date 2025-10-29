from typing import Any, Awaitable, Callable
import json
from urllib.parse import parse_qs
import math


def parse_int(value: str) -> int | None:
    try:
        if value is None or value == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None

def fibonacci(n: int) -> int:
    if n == 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

async def send_json(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    payload: dict[str, Any] | list[Any] | None,
) -> None:
    body_bytes = json.dumps(payload if payload is not None else {}).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(body_bytes)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body_bytes})

async def read_body_bytes(
    receive: Callable[[], Awaitable[dict[str, Any]]]
) -> bytes:
    chunks: list[bytes] = []
    more = True
    while more:
        message = await receive()
        if message.get("type") != "http.request":
            break
        body = message.get("body", b"") or b""
        if body:
            chunks.append(body)
        more = bool(message.get("more_body"))
    return b"".join(chunks)

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
    if scope.get("type") != "http":
        await send(
            {
                "type": "http.response.start",
                "status": 404,
                "headers": [(b"content-type", b"application/json; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": b"{}"})
        return

    method: str = scope.get("method", "GET").upper()
    raw_path: bytes = scope.get("raw_path") or scope.get("path", "/").encode()
    path: str = (raw_path.decode("utf-8") if isinstance(raw_path, (bytes, bytearray)) else str(raw_path))

    if method != "GET":
        await send_json(send, 404, {})
        return

    if path == "/factorial":
        query_bytes: bytes = scope.get("query_string", b"") or b""
        qs = parse_qs(query_bytes.decode("utf-8"), keep_blank_values=True)
        n_values = qs.get("n")
        if not n_values:
            await send_json(send, 422, {})
            return
        n_raw = n_values[0]
        n = parse_int(n_raw)
        if n is None:
            await send_json(send, 422, {})
            return
        if n < 0:
            await send_json(send, 400, {})
            return
        await send_json(send, 200, {"result": math.factorial(n)})
        return

    if path.startswith("/fibonacci"):
        parts = path.split("/")
        if len(parts) != 3 or parts[2] == "":
            await send_json(send, 422, {})
            return
        n = parse_int(parts[2])
        if n is None:
            await send_json(send, 422, {})
            return
        if n < 0:
            await send_json(send, 400, {})
            return
        await send_json(send, 200, {"result": fibonacci(n)})
        return

    if path == "/mean":
        body = await read_body_bytes(receive)
        if not body:
            await send_json(send, 422, {})
            return
        try:
            data = json.loads(body.decode("utf-8"))
        except Exception:
            await send_json(send, 422, {})
            return
        if not isinstance(data, list):
            await send_json(send, 422, {})
            return
        if len(data) == 0:
            await send_json(send, 400, {})
            return
        total = 0.0
        count = 0
        for item in data:
            if not isinstance(item, (int, float)):
                await send_json(send, 422, {})
                return
            total += float(item)
            count += 1
        result = total / count if count > 0 else 0.0
        await send_json(send, 200, {"result": result})
        return

    await send_json(send, 404, {})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
