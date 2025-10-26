from typing import Any, Awaitable, Callable

import json
from http import HTTPStatus
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
    if scope.get("type") == "lifespan":
        while True:
            message = await receive()
            msg_type = message.get("type")
            if msg_type == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif msg_type == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        
    elif scope.get("type") != "http":
        return

    method = scope.get("method", "").upper()
    path = scope.get("path", "")

    async def send_json(status: int, payload: dict[str, Any] | None = None) -> None:
        body_bytes = json.dumps(payload or {}).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": int(status),
                "headers": [
                    (b"content-type", b"application/json; charset=utf-8"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body_bytes})

    async def read_body() -> bytes:
        chunks: list[bytes] = []
        more_body = True
        while more_body:
            message = await receive()
            if message.get("type") != "http.request":
                break
            body_part: bytes = message.get("body", b"") or b""
            if body_part:
                chunks.append(body_part)
            more_body = bool(message.get("more_body", False))
        return b"".join(chunks)

    if method == "GET" and path == "/factorial":
        raw_qs = scope.get("query_string", b"") or b""
        query = parse_qs(raw_qs.decode("utf-8"))
        values = query.get("n")
        if not values or values[0] == "":
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "parameter 'n' is required"})
            return
        try:
            n = int(values[0])
        except (TypeError, ValueError):
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "parameter 'n' must be an integer"})
            return
        if n < 0:
            await send_json(HTTPStatus.BAD_REQUEST, {"detail": "n must be non-negative"})
            return
        result = 1
        for i in range(2, n + 1):
            result *= i
        await send_json(HTTPStatus.OK, {"result": result})
        return

    if method == "GET" and (path == "/fibonacci" or path.startswith("/fibonacci/")):
        if path == "/fibonacci":
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "path parameter is required"})
            return
        param = path.removeprefix("/fibonacci/")
        if param == "":
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "path parameter is required"})
            return
        try:
            n = int(param)
        except ValueError:
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "path parameter must be an integer"})
            return
        if n < 0:
            await send_json(HTTPStatus.BAD_REQUEST, {"detail": "n must be non-negative"})
            return
        if n == 0:
            fib_val = 0
        elif n == 1:
            fib_val = 1
        else:
            prev, curr = 0, 1
            for _ in range(2, n + 1):
                prev, curr = curr, prev + curr
            fib_val = curr
        await send_json(HTTPStatus.OK, {"result": fib_val})
        return

    if method == "GET" and path == "/mean":
        body = await read_body()
        if not body:
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "JSON array body is required"})
            return
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "invalid JSON"})
            return
        if not isinstance(data, list):
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "body must be a JSON array"})
            return
        if len(data) == 0:
            await send_json(HTTPStatus.BAD_REQUEST, {"detail": "array must be non-empty"})
            return
        numbers: list[float] = []
        for item in data:
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                await send_json(HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "array must contain only numbers"})
                return
            numbers.append(float(item))
        mean_value = sum(numbers) / len(numbers)
        await send_json(HTTPStatus.OK, {"result": mean_value})
        return

    await send_json(HTTPStatus.NOT_FOUND, {"detail": "not found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
