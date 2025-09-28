import json
from math import factorial as math_factorial
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


async def _send_json(
        send: Callable[[dict[str, Any]], Awaitable[None]],
        status: int,
        payload: dict[str, Any] | None = None,
) -> None:
    """Утилита для отправки JSON-ответа по ASGI.
    """
    body_bytes = b""
    if payload is not None:
        body_bytes = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    headers = [
        (b"content-type", b"application/json; charset=utf-8"),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body_bytes})


async def _receive_body(
        receive: Callable[[], Awaitable[dict[str, Any]]]
) -> bytes:
    """Считать всё тело запроса (если есть).
    """
    chunks: list[bytes] = []
    more_body = True
    while more_body:
        message = await receive()
        if message["type"] != "http.request":
            # Нестандартные сообщения игнорируем (для простоты).
            break
        chunks.append(message.get("body", b"") or b"")
        more_body = message.get("more_body", False)
    return b"".join(chunks)


def _fib(n: int) -> int:
    """ Реализация Фибонначи.
    """
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


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
    # обработка только HTTP-запросов.
    if scope.get("type") != "http":
        await _send_json(send, 404, {"detail": "Not Found"})
        return

    method: str = scope.get("method", "GET").upper()
    path: str = scope.get("path", "")
    query_raw: bytes = scope.get("query_string", b"")

    # GET /factorial?n=...
    if method == "GET" and path == "/factorial":
        query = parse_qs(query_raw.decode("utf-8", errors="ignore"))
        values = query.get("n")

        if not values or values[0] is None or values[0] == "":
            await _send_json(send, 422,
                             {"detail": "Query parameter 'n' is required and must be an integer."})
            return

        try:
            n = int(values[0])
        except (ValueError, TypeError):
            await _send_json(send, 422, {"detail": "Query parameter 'n' must be an integer."})
            return

        if n < 0:
            await _send_json(send, 400, {"detail": "Query parameter 'n' must be non-negative."})
            return

        result = math_factorial(n)
        await _send_json(send, 200, {"result": result})
        return

    # GET /fibonacci/<n>
    if method == "GET" and path.startswith("/fibonacci"):
        parts = path.strip("/").split("/")
        if len(parts) != 2 or parts[0] != "fibonacci":
            # Нет сегмента с числом -> неверный формат пути
            await _send_json(send, 422,
                             {"detail": "Path must be /fibonacci/<n> where n is an integer."})
            return

        raw_n = parts[1]
        try:
            n = int(raw_n)
        except (ValueError, TypeError):
            await _send_json(send, 422, {"detail": "Path parameter 'n' must be an integer."})
            return

        if n < 0:
            await _send_json(send, 400, {"detail": "Path parameter 'n' must be non-negative."})
            return

        result = _fib(n)
        await _send_json(send, 200, {"result": result})
        return

    # GET /mean  (JSON-массив чисел в теле)
    if method == "GET" and path == "/mean":
        body = await _receive_body(receive)

        if not body:
            await _send_json(send, 422,
                             {"detail": "Request body must be a JSON array of numbers."})
            return

        try:
            data = json.loads(body.decode("utf-8"))
        except json.JSONDecodeError:
            await _send_json(send, 422, {"detail": "Invalid JSON."})
            return

        # В тестах json=None то есть ожидается 422; None обрабатываем как неподдерживаемый формат
        if data is None or not isinstance(data, list):
            await _send_json(send, 422,
                             {"detail": "Request body must be a JSON array of numbers."})
            return

        if len(data) == 0:
            await _send_json(send, 400, {"detail": "Array must not be empty."})
            return

        nums: list[float] = []
        for item in data:
            if isinstance(item, bool):
                await _send_json(send, 422, {"detail": "Array must contain only numbers."})
                return
            if isinstance(item, (int, float)):
                nums.append(float(item))
            else:
                await _send_json(send, 422, {"detail": "Array must contain only numbers."})
                return

        mean_value = sum(nums) / len(nums)
        await _send_json(send, 200, {"result": mean_value})
        return

    # Всё остальное — 404
    await _send_json(send, 404, {"detail": "Not Found"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
