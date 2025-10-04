from typing import Any, Awaitable, Callable
import json
from math import prod
from urllib.parse import parse_qs


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
        await _send_json(send, {"detail": "unsupported scope type"}, status=422)
        return

    method = scope.get("method", "GET").upper()
    path: str = scope.get("path", "/")
    query = parse_qs((scope.get("query_string") or b"").decode(
        "utf-8"), keep_blank_values=True)

    if path.startswith("/fibonacci/"):
        n_str = path[len("/fibonacci/"):].strip("/")
        if n_str == "":
            await _send_json(send, {"detail": "n is required"}, status=422)
            return
        try:
            n = int(n_str)
        except ValueError:
            await _send_json(send, {"detail": "n must be an integer"}, status=422)
            return
        if n < 0:
            await _send_json(send, {"detail": "n must be non-negative"}, status=400)
            return

        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        await _send_json(send, {"result": a}, status=200)
        return

    if path == "/factorial":
        if method != "GET":
            await _send_json(send, {"detail": "not found"}, status=404)
            return

        raw = query.get("n", [None])[0]
        if raw is None or raw == "":
            await _send_json(send, {"detail": "n is required"}, status=422)
            return
        try:
            n = int(raw)
        except ValueError:
            await _send_json(send, {"detail": "n must be an integer"}, status=422)
            return
        if n < 0:
            await _send_json(send, {"detail": "n must be non-negative"}, status=400)
            return

        result = 1 if n == 0 else prod(range(1, n + 1))
        await _send_json(send, {"result": result}, status=200)
        return

    if path == "/mean":
        if method != "GET":
            await _send_json(send, {"detail": "not found"}, status=404)
            return

        body_bytes = await _read_body(receive)
        if not body_bytes:
            await _send_json(send, {"detail": "json body required (array of numbers)"}, status=422)
            return

        try:
            data = json.loads(body_bytes.decode("utf-8"))
        except json.JSONDecodeError:
            await _send_json(send, {"detail": "invalid JSON"}, status=422)
            return

        if not isinstance(data, list):
            await _send_json(send, {"detail": "body must be a JSON array"}, status=422)
            return

        if len(data) == 0:
            await _send_json(send, {"detail": "array must not be empty"}, status=400)
            return

        try:
            nums = [float(x) for x in data]
        except (TypeError, ValueError):
            await _send_json(send, {"detail": "array must contain only numbers"}, status=422)
            return

        mean_value = sum(nums) / len(nums)
        await _send_json(send, {"result": mean_value}, status=200)
        return

    await _send_json(send, {"detail": "not found"}, status=404)


async def _read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    body = b""
    more = True
    while more:
        message = await receive()
        if message["type"] != "http.request":
            break
        body += message.get("body", b"")
        more = message.get("more_body", False)
    return body


async def _send_json(send: Callable[[dict[str, Any]], Awaitable[None]], payload: dict, status: int = 200):
    body = json.dumps(payload).encode("utf-8")
    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
