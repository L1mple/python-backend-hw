from typing import Any, Awaitable, Callable
import json
import math
from urllib.parse import parse_qs


async def _send_json(send: Callable[[dict[str, Any]], Awaitable[None]], status: int, payload: dict[str, Any] | None = None) -> None:
    body_bytes = json.dumps(payload or {}).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body_bytes})


def _parse_int(value: str | None) -> tuple[bool, int | None]:
    if value is None:
        return False, None
    try:
        return True, int(value)
    except Exception:
        return False, None


def _fibonacci(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return b


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
        await _send_json(send, 404, {"detail": "Not Found"})
        return

    method: str = scope.get("method", "GET")
    path: str = scope.get("path", "")

    if method != "GET":
        await _send_json(send, 404, {"detail": "Not Found"})
        return

    # /factorial?n=<int>
    if path == "/factorial":
        query_raw: bytes = scope.get("query_string", b"")
        query_params = parse_qs(query_raw.decode())
        values = query_params.get("n")
        if not values or len(values) != 1:
            await _send_json(send, 422, {"detail": "Invalid query params"})
            return
        ok, n = _parse_int(values[0])
        if not ok:
            await _send_json(send, 422, {"detail": "Parameter n must be integer"})
            return
        if n is None or n < 0:
            await _send_json(send, 400, {"detail": "Invalid value for n, must be non-negative"})
            return
        result = math.factorial(n)
        await _send_json(send, 200, {"result": result})
        return

    # /fibonacci/{n}
    if path.startswith("/fibonacci/") and path.count("/") == 2:
        n_str = path.split("/")[-1]
        ok, n = _parse_int(n_str)
        if not ok:
            await _send_json(send, 422, {"detail": "Path parameter n must be integer"})
            return
        if n is None or n < 0:
            await _send_json(send, 400, {"detail": "Invalid value for n, must be non-negative"})
            return
        result = _fibonacci(n)
        await _send_json(send, 200, {"result": result})
        return

    if path == "/mean":
        body = b""
        while True:
            message = await receive()
            body += message.get("body", b"")
            if not message.get("more_body", False):
                break

        if not body:
            await _send_json(send, 422, {"detail": "Request body required"})
            return

        try:
            data = json.loads(body)
        except Exception:
            await _send_json(send, 422, {"detail": "Invalid JSON"})
            return

        if not isinstance(data, list):
            await _send_json(send, 422, {"detail": "Body must be a JSON array"})
            return

        if len(data) == 0:
            await _send_json(send, 400, {"detail": "Array must be non-empty"})
            return

        def _is_number(x: Any) -> bool:
            # bool is a subclass of int -> exclude
            return isinstance(x, (int, float)) and not isinstance(x, bool)

        if not all(_is_number(x) for x in data):
            await _send_json(send, 422, {"detail": "Array must contain only numbers"})
            return

        nums = [float(x) for x in data]
        mean_value = sum(nums) / len(nums)
        await _send_json(send, 200, {"result": mean_value})
        return

    # default 404
    await _send_json(send, 404, {"detail": "Not Found"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
