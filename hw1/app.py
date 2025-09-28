import json
import math
from http import HTTPStatus
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


async def _send_json(
    send: Callable[[dict[str, Any]], Awaitable[None]], status: int, payload: dict
):
    body = json.dumps(payload).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"application/json")],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def _read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    body = b""
    more = True
    while more:
        event = await receive()
        if event["type"] == "http.request":
            body += event.get("body", b"")
            more = event.get("more_body", False)
    return body


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
    if scope["type"] != "http":
        await _send_json(send, 422, {"error": "Unsupported scope"})
        return

    method = scope["method"]
    path = scope["path"]

    ################## /fibonacci/<n> ##################
    if method == "GET" and path.startswith("/fibonacci"):
        if path == "/fibonacci":
            await _send_json(
                send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Missing number"}
            )
            return
        sub = path[len("/fibonacci") :]
        if not sub.startswith("/"):
            await _send_json(
                send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Invalid path"}
            )
            return
        num_str = sub[1:]
        if not num_str or not num_str.lstrip("-").isdigit():
            await _send_json(
                send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Invalid number"}
            )
            return
        n = int(num_str)
        if n < 0:
            await _send_json(
                send, HTTPStatus.BAD_REQUEST, {"error": "n must be non-negative"}
            )
            return
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        await _send_json(send, HTTPStatus.OK, {"result": a})
        return

    ################## /factorial?n=... ##################
    if method == "GET" and path == "/factorial":
        query = parse_qs(scope.get("query_string", b"").decode())
        raw = query.get("n")
        n_str = raw[0] if raw else None
        if n_str is None or n_str == "":
            await _send_json(
                send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Missing n"}
            )
            return
        try:
            n = int(n_str)
        except ValueError:
            await _send_json(
                send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "n is not int"}
            )
            return
        if n < 0:
            await _send_json(
                send, HTTPStatus.BAD_REQUEST, {"error": "n must be non-negative"}
            )
            return
        await _send_json(send, HTTPStatus.OK, {"result": math.factorial(n)})
        return

    ################## /mean?numbers=<n1, n2, n3> ##################
    # в примере вызова list в запросе, но в задании со слайда он в теле запроса
    if method == "GET" and path == "/mean":
        body = await _read_body(receive)
        if not body:
            await _send_json(
                send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Empty body"}
            )
            return
        try:
            data = json.loads(body.decode())
        except Exception:
            await _send_json(
                send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Invalid JSON"}
            )
            return
        if not isinstance(data, list):
            await _send_json(
                send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Expected list"}
            )
            return
        if not data:
            await _send_json(send, HTTPStatus.BAD_REQUEST, {"error": "Empty list"})
            return
        if not all(isinstance(x, (int, float)) for x in data):
            await _send_json(
                send,
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "List must contain numbers"},
            )
            return
        await _send_json(send, HTTPStatus.OK, {"result": sum(data) / len(data)})
        return

    await _send_json(send, HTTPStatus.NOT_FOUND, {"error": "Not found"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
