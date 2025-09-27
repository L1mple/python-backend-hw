from http import HTTPStatus
from typing import (
    Any,
    Awaitable,
    Callable,
)
import json as jsonlib
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
    # assert scope['type'] == 'http'
    method: str = scope.get("method", "GET")
    path: str = scope.get("path", "/")
    query_string: bytes = scope.get("query_string", b"")

    async def send_json(status: HTTPStatus, payload: dict[str, Any] | None = None) -> None:
        await send({
            "type": "http.response.start",
            "status": int(status),
            "headers": [
                [b"content-type", b"application/json"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": jsonlib.dumps(payload or {}).encode("utf-8"),
        })

    # Route handling
    if method == "GET" and path == "/factorial":
        params = parse_qs(query_string.decode("utf-8")) if query_string else {}
        raw_n = params.get("n", [None])[0]
        if raw_n is None or raw_n == "":
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
            return
        try:
            n = int(raw_n)
        except (TypeError, ValueError):
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
            return
        if n < 0:
            await send_json(HTTPStatus.BAD_REQUEST)
            return
        result = 1
        for i in range(2, n + 1):
            result *= i
        await send_json(HTTPStatus.OK, {"result": result})
        return

    if method == "GET" and path.startswith("/fibonacci"):
        parts = path.split("/")
        raw_n = parts[2] if len(parts) > 2 and parts[2] != "" else None
        if raw_n is None:
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
            return
        try:
            n = int(raw_n)
        except (TypeError, ValueError):
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
            return
        if n < 0:
            await send_json(HTTPStatus.BAD_REQUEST)
            return
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        await send_json(HTTPStatus.OK, {"result": a})
        return

    if method == "GET" and path == "/mean":
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            msg_type = message.get("type")
            if msg_type == "http.disconnect":
                break
            if msg_type != "http.request":
                continue
            body += message.get("body", b"")
            more_body = message.get("more_body", False)
        if body:
            try:
                data = jsonlib.loads(body.decode("utf-8"))
            except jsonlib.JSONDecodeError:
                await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            if not isinstance(data, list):
                await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            if len(data) == 0:
                await send_json(HTTPStatus.BAD_REQUEST)
                return
            try:
                numbers = [float(x) for x in data]
            except (TypeError, ValueError):
                await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
                return
            mean_value = sum(numbers) / len(numbers)
            await send_json(HTTPStatus.OK, {"result": mean_value})
            return

        params = parse_qs(query_string.decode("utf-8")) if query_string else {}
        numbers_param = params.get("numbers", [None])[0]
        if numbers_param is None:
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
            return
        items = [p for p in numbers_param.split(',') if p != ""]
        if len(items) == 0:
            await send_json(HTTPStatus.BAD_REQUEST)
            return
        try:
            numbers = [float(x) for x in items]
        except (TypeError, ValueError):
            await send_json(HTTPStatus.UNPROCESSABLE_ENTITY)
            return
        mean_value = sum(numbers) / len(numbers)
        await send_json(HTTPStatus.OK, {"result": mean_value})
        return

    await send_json(HTTPStatus.NOT_FOUND)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
