import math
from http import HTTPStatus
from typing import Any, Awaitable, Callable
import json


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

    async def send_response(status: int, body: dict[str, Any] | None = None):
        content = b""
        headers = [(b"content-type", b"application/json")]
        if body is not None:
            content = json.dumps(body).encode("utf-8")
            headers.append((b"content-length", str(len(content)).encode("utf-8")))
        else:
            headers.append((b"content-length", b"0"))

        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        await send({"type": "http.response.body", "body": content})

    # --- lifespan events (startup/shutdown) ---
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    # --- обычные HTTP запросы ---
    if scope["type"] != "http":
        return

    method = scope["method"]
    path = scope["path"]

    # factorial
    if method == "GET" and path == "/factorial":
        query_string = scope.get("query_string", b"").decode()
        query = dict(
            (q.split("=") + [""])[:2]
            for q in query_string.split("&")
            if q
        )
        n_str = query.get("n")
        if n_str is None or n_str == "":
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)
        try:
            n = int(n_str)
        except ValueError:
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)
        if n < 0:
            return await send_response(HTTPStatus.BAD_REQUEST)
        return await send_response(HTTPStatus.OK, {"result": math.factorial(n)})

    # fibonacci
    if method == "GET" and path.startswith("/fibonacci"):
        parts = path.split("/")
        if len(parts) != 3:
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)
        try:
            n = int(parts[2])
        except ValueError:
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)
        if n < 0:
            return await send_response(HTTPStatus.BAD_REQUEST)
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return await send_response(HTTPStatus.OK, {"result": a})

    # mean
    if method == "GET" and path == "/mean":
        body_event = await receive()
        if body_event.get("type") != "http.request":
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)
        body_bytes = body_event.get("body", b"") or b""
        if not body_bytes:
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)

        try:
            data = json.loads(body_bytes.decode())
        except json.JSONDecodeError:
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)

        if not isinstance(data, list):
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)
        if len(data) == 0:
            return await send_response(HTTPStatus.BAD_REQUEST)

        try:
            nums = [float(x) for x in data]
        except (TypeError, ValueError):
            return await send_response(HTTPStatus.UNPROCESSABLE_ENTITY)

        return await send_response(
            HTTPStatus.OK, {"result": sum(nums) / len(nums)}
        )

    # всё остальное → 404
    return await send_response(HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
