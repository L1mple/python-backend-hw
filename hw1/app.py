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
    # Обработка lifespan для тестового клиента
    if scope.get("type") == "lifespan":
        # consume one message and reply startup.complete, then wait for shutdown
        # Startup
        await receive()
        await send({"type": "lifespan.startup.complete"})
        # Shutdown
        await receive()
        await send({"type": "lifespan.shutdown.complete"})
        return

    # Обрабатываем только HTTP запросы
    if scope.get("type") != "http":
        return

    method = scope.get("method", "").upper()
    path = scope.get("path", "")

    # Для неподдерживаемых методов возвращаем 422
    if method != "GET":
        await _send_json(send, {"error": "Unprocessable"}, status=422)
        return

    # Маршрутизация
    if path.startswith("/fibonacci"):
        # Ожидаем форму /fibonacci/<n>
        parts = path.split("/")
        # ['', 'fibonacci', '<n>'] ожидается длина 3
        if len(parts) != 3 or not parts[2]:
            await _send_json(send, {"error": "Unprocessable"}, status=422)
            return
        n_str = parts[2]
        # n должно быть целым числом
        try:
            n = int(n_str)
        except Exception:
            await _send_json(send, {"error": "Unprocessable"}, status=422)
            return
        if n < 0:
            await _send_json(send, {"error": "Bad Request"}, status=400)
            return
        result = _fib(n)
        await _send_json(send, {"result": result}, status=200)
        return

    if path == "/factorial":
        # Параметр n из query_string
        raw_qs = scope.get("query_string", b"") or b""
        try:
            qs = raw_qs.decode()
        except Exception:
            qs = ""
        params = _parse_query(qs)
        n_val = params.get("n")
        if n_val is None or n_val == "":
            await _send_json(send, {"error": "Unprocessable"}, status=422)
            return
        try:
            n = int(n_val)
        except Exception:
            await _send_json(send, {"error": "Unprocessable"}, status=422)
            return
        if n < 0:
            await _send_json(send, {"error": "Bad Request"}, status=400)
            return
        await _send_json(send, {"result": _fact(n)}, status=200)
        return

    if path == "/mean":
        # По тестам JSON-тело: массив чисел, GET /mean
        body = await _read_body(receive)
        if body is None:
            await _send_json(send, {"error": "Unprocessable"}, status=422)
            return
        # Ожидаем JSON-массив
        import json

        try:
            data = json.loads(body)
        except Exception:
            await _send_json(send, {"error": "Unprocessable"}, status=422)
            return
        if not isinstance(data, list):
            await _send_json(send, {"error": "Bad Request"}, status=400)
            return
        if len(data) == 0:
            await _send_json(send, {"error": "Bad Request"}, status=400)
            return
        # Валидация чисел
        numbers: list[float] = []
        for item in data:
            if isinstance(item, (int, float)):
                numbers.append(float(item))
            else:
                await _send_json(send, {"error": "Unprocessable"}, status=422)
                return
        mean_value = sum(numbers) / len(numbers)
        await _send_json(send, {"result": float(mean_value)}, status=200)
        return

    # Любой другой путь — 404
    await _send_json(send, {"error": "Not Found"}, status=404)


def _fib(n: int) -> int:
    if n == 0:
        return 0
    if n == 1:
        return 1
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def _fact(n: int) -> int:
    res = 1
    for i in range(2, n + 1):
        res *= i
    return res


def _parse_query(qs: str = "") -> dict[str, str]:
    # Простейший парсер query строки: key=value&key2=value2
    result: dict[str, str] = {}
    if not qs:
        return result
    for pair in qs.split("&"):
        if not pair:
            continue
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k] = v
        else:
            result[pair] = ""
    return result


async def _read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes | None:
    body = b""
    more = True
    while more:
        message = await receive()
        if message.get("type") != "http.request":
            continue
        body += message.get("body", b"") or b""
        more = message.get("more_body", False)
        if not more:
            break
    return body if body != b"" else None


async def _send_json(send: Callable[[dict[str, Any]], Awaitable[None]], data: dict[str, Any], status: int = 200) -> None:
    import json

    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [[b"content-type", b"application/json"]],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": json.dumps(data).encode("utf-8"),
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
