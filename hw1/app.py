from typing import Any, Awaitable, Callable
import json
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
    
    method = scope.get("method", "").upper()
    path = scope.get("path", "")

    async def send_json(status: int, payload: dict[str, Any] | None = None) -> None:
        body_bytes = json.dumps(payload or {}).encode("utf-8")
        headers = [
            (b"content-type", b"application/json; charset=utf-8"),
        ]
        await send({
            "type": "http.response.start",
            "status": status,
            "headers": headers,
        })
        await send({
            "type": "http.response.body",
            "body": body_bytes,
        })

    async def read_body() -> bytes:
        chunks: list[bytes] = []
        while True:
            message = await receive()
            if message.get("type") != "http.request":
                continue
            body = message.get("body", b"") or b""
            if body:
                chunks.append(body)
            if not message.get("more_body", False):
                break
        return b"".join(chunks)

    if method != "GET":
        await send_json(404, {"detail": "Not Found"})
        return

    if path == "/factorial":
        raw_qs = scope.get("query_string", b"")
        qs = parse_qs(raw_qs.decode("utf-8"), keep_blank_values=True)
        values = qs.get("n")
        if not values or values[0] == "":
            await send_json(422, {"detail": "Query parameter 'n' is required"})
            return
        try:
            n = int(values[0])
        except ValueError:
            await send_json(422, {"detail": "Query parameter 'n' must be integer"})
            return
        if n < 0:
            await send_json(400, {"detail": "'n' must be non-negative"})
            return
        # factorial
        result = 1
        for i in range(2, n + 1):
            result *= i
        await send_json(200, {"result": result})
        return

    if path == "/mean":
        body = await read_body()
        if not body:
            await send_json(422, {"detail": "JSON body is required"})
            return
        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            await send_json(422, {"detail": "Malformed JSON"})
            return
        if data is None:
            await send_json(422, {"detail": "JSON body is required"})
            return
        if not isinstance(data, list) or len(data) == 0:
            await send_json(400, {"detail": "Expected non-empty JSON array of numbers"})
            return
        # Validate all elements are numbers (int or float)
        if not all((isinstance(x, (int, float)) and not isinstance(x, bool)) for x in data):
            await send_json(400, {"detail": "Array must contain only numbers"})
            return
        total = float(sum(float(x) for x in data))
        mean_value = total / len(data)
        await send_json(200, {"result": mean_value})
        return

    if path.startswith("/fibonacci"):
        if path == "/fibonacci":
            await send_json(422, {"detail": "Path parameter 'n' is required"})
            return
        if not path.startswith("/fibonacci/"):
            await send_json(404, {"detail": "Not Found"})
            return
        raw_n = path[len("/fibonacci/") :]
        if raw_n == "":
            await send_json(422, {"detail": "Path parameter 'n' is required"})
            return
        try:
            n = int(raw_n)
        except ValueError:
            await send_json(422, {"detail": "Path parameter 'n' must be integer"})
            return
        if n < 0:
            await send_json(400, {"detail": "'n' must be non-negative"})
            return
        # fibonacci
        if n == 0:
            fib = 0
        elif n == 1:
            fib = 1
        else:
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            fib = b
        await send_json(200, {"result": fib})
        return

    await send_json(404, {"detail": "Not Found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
