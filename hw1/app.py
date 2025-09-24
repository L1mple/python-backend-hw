from typing import Any, Awaitable, Callable


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
    # TODO: Ваша реализация здесь
    if scope.get("type") != "http":
        await send({"type": "http.response.start", "status": 404, "headers": []})
        await send({"type": "http.response.body", "body": b""})
        return

    method = scope.get("method", "").upper()
    path = scope.get("path", "")

    async def send_json(status: int, data: dict[str, Any] | None = None) -> None:
        import json

        body_bytes = json.dumps(data or {}).encode("utf-8")
        headers = [
            (b"content-type", b"application/json; charset=utf-8"),
            (b"content-length", str(len(body_bytes)).encode("ascii")),
        ]
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": body_bytes})

    # Helper to read the entire request body (single chunk expected for tests)
    async def read_body() -> bytes:
        body_chunks: list[bytes] = []
        more = True
        while more:
            message = await receive()
            if message.get("type") != "http.request":
                break
            body_chunks.append(message.get("body", b""))
            more = message.get("more_body", False)
        return b"".join(body_chunks)

    # Only GET endpoints are supported in tests
    if method != "GET":
        await send_json(404, {})
        return

    # /factorial?n=...
    if path == "/factorial":
        # Parse query string from scope
        raw_qs: bytes = scope.get("query_string", b"") or b""
        from urllib.parse import parse_qs

        qs = parse_qs(raw_qs.decode("utf-8"), keep_blank_values=True)
        if "n" not in qs or qs["n"] is None or len(qs["n"]) == 0:
            await send_json(422, {})
            return
        n_str = qs["n"][0]
        # Reject empty string or non-integer
        try:
            n = int(n_str)
        except Exception:
            await send_json(422, {})
            return
        if n < 0:
            await send_json(400, {})
            return

        # Compute factorial iteratively
        result = 1
        for i in range(2, n + 1):
            result *= i
        await send_json(200, {"result": result})
        return

    # /fibonacci/{n}
    if path.startswith("/fibonacci"):
        # Expect format /fibonacci/<n>
        parts = path.split("/")
        # ['', 'fibonacci', '<n>'] expected length >= 3
        if len(parts) < 3 or parts[2] == "":
            await send_json(422, {})
            return
        n_str = parts[2]
        try:
            n = int(n_str)
        except Exception:
            await send_json(422, {})
            return
        if n < 0:
            await send_json(400, {})
            return
        # Compute nth Fibonacci (F0 = 0, F1 = 1)
        if n == 0:
            fib_n = 0
        elif n == 1:
            fib_n = 1
        else:
            a, b = 0, 1
            for _ in range(2, n + 1):
                a, b = b, a + b
            fib_n = b
        await send_json(200, {"result": fib_n})
        return

    # /mean with JSON body list
    if path == "/mean":
        # Read JSON from body
        body = await read_body()
        if not body:
            await send_json(422, {})
            return
        import json

        try:
            payload = json.loads(body)
        except Exception:
            await send_json(422, {})
            return
        if payload is None:
            await send_json(422, {})
            return
        if not isinstance(payload, list):
            await send_json(422, {})
            return
        if len(payload) == 0:
            await send_json(400, {})
            return
        # Validate numeric entries
        numbers: list[float] = []
        for item in payload:
            if not isinstance(item, (int, float)):
                await send_json(422, {})
                return
            numbers.append(float(item))
        mean_value = sum(numbers) / len(numbers)
        await send_json(200, {"result": mean_value})
        return

    # Fallback: not found
    await send_json(404, {})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
