import json, math
from typing import Any, Awaitable, Callable
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

    # helper для ответа
    async def send_response(status: int, payload: dict[str, Any]):
        body = json.dumps(payload).encode()
        headers = [(b"content-type", b"application/json")]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body})

    # поддержка lifespan, чтобы тестовый клиент не падал
    if scope.get("type") == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    if scope.get("type") != "http":
        return

    method = scope["method"].upper()
    path = scope["path"]

    # factorial: /factorial?n=5
    if path == "/factorial" and method == "GET":
        qs = parse_qs(scope.get("query_string", b"").decode())
        n_values = qs.get("n")
        if not n_values or n_values[0] == "":
            return await send_response(422, {"detail": "Missing or invalid parameter n"})
        try:
            n = int(n_values[0])
        except ValueError:
            return await send_response(422, {"detail": "Parameter n must be integer"})
        if n < 0:
            return await send_response(400, {"detail": "n must be non-negative"})
        return await send_response(200, {"result": math.factorial(n)})

    # fibonacci: /fibonacci/<n>
    if path.startswith("/fibonacci") and method == "GET":
        parts = path.split("/")
        if len(parts) != 3 or not parts[2]:
            return await send_response(422, {"detail": "Invalid path parameter"})
        try:
            n = int(parts[2])
        except ValueError:
            return await send_response(422, {"detail": "Path parameter must be integer"})
        if n < 0:
            return await send_response(400, {"detail": "n must be non-negative"})
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return await send_response(200, {"result": a})

    # mean: /mean с json=[...]
    if path == "/mean" and method == "GET":
        body_event = await receive()
        body_bytes = body_event.get("body", b"")
        if not body_bytes:
            return await send_response(422, {"detail": "Body is required"})
        try:
            data = json.loads(body_bytes.decode())
        except Exception:
            return await send_response(422, {"detail": "Invalid JSON"})
        if not isinstance(data, list):
            return await send_response(422, {"detail": "Body must be a list"})
        if len(data) == 0:
            return await send_response(400, {"detail": "List must not be empty"})
        try:
            numbers = [float(x) for x in data]
        except Exception:
            return await send_response(422, {"detail": "List must contain numbers"})
        result = sum(numbers) / len(numbers)
        return await send_response(200, {"result": result})

    # если ничего не подошло
    return await send_response(404, {"detail": "Not Found"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
