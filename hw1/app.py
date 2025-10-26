import json
from math import factorial
from typing import Any, Awaitable, Callable, List
from urllib.parse import parse_qs

import uvicorn

ALLOWED_PATHS = ["/factorial", "/mean", "/fibonacci"]


def calculate_factorial(value: int) -> int:
    """Функция для расчета факториала"""
    return factorial(value)


def calculate_fibonacсі(n: int) -> int:
    """Функция для расчета n-ого числа фибоначи"""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return b


def calculate_mean(data: List[float]):
    """Функция для расчета среднего из массива чисел"""
    result = sum(data) / len(data)
    return result


async def _read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    body = b""
    more = True
    while more:
        message = await receive()
        body += message.get("body", b"")
        more = message.get("more_body", False)
    return body


async def _send_json(send, status: int, payload: dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = [
        [b"content-type", b"application/json; charset=utf-8"],
        [b"content-length", str(len(body)).encode("utf-8")],
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body, "more_body": False})


def _parse_query(scope: dict[str, Any]) -> dict[str, list[str]]:
    qs_bytes = scope.get("query_string", b"") or b""
    return parse_qs(qs_bytes.decode("utf-8"), keep_blank_values=True)


def _parse_int_strict(s: str) -> int:
    s2 = s.strip()
    if s2 == "":
        raise ValueError("empty")
    if s2[0] in "+-":
        if len(s2) == 1 or not s2[1:].isdigit():
            raise ValueError("non-integer")
    else:
        if not s2.isdigit():
            raise ValueError("non-integer")
    return int(s2, 10)


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
        await _send_json(send, 404, {"error": "Not Found"})
        return

    path = scope.get("path") or ""

    if path not in ALLOWED_PATHS and not path.startswith("/fibonacci"):
        await _send_json(send, 404, {"error": "Not Found"})
        return

    try:
        if path == "/factorial":
            params = _parse_query(scope)
            values = params.get("n", [])
            if not values:
                return await _send_json(send, 422, {"error": "missing 'n'"})
            try:
                n = _parse_int_strict(values[0])
            except ValueError:
                return await _send_json(send, 422, {"error": "n must be integer"})
            if n < 0:
                return await _send_json(send, 400, {"error": "n must be >= 0"})
            return await _send_json(send, 200, {"result": calculate_factorial(n)})

        if path.startswith("/fibonacci"):
            suffix = path[len("/fibonacci") :]
            if not suffix or suffix == "/":
                return await _send_json(send, 422, {"error": "missing path param 'n'"})
            if suffix[0] == "/":
                raw = suffix[1:]
            else:
                raw = suffix
            try:
                n = _parse_int_strict(raw)
            except ValueError:
                return await _send_json(send, 422, {"error": "n must be integer"})
            if n < 0:
                return await _send_json(send, 400, {"error": "n must be >= 0"})
            return await _send_json(send, 200, {"result": calculate_fibonacсі(n)})

        if path == "/mean":
            body = await _read_body(receive)
            if not body:
                return await _send_json(send, 422, {"error": "missing JSON body"})
            try:
                data = json.loads(body.decode("utf-8"))
            except Exception:
                return await _send_json(send, 422, {"error": "invalid JSON"})
            if data is None or not isinstance(data, list):
                return await _send_json(send, 422, {"error": "body must be JSON array"})
            if len(data) == 0:
                return await _send_json(send, 400, {"error": "array must be non-empty"})
            nums: list[float] = []
            for item in data:
                if isinstance(item, (int, float)):
                    nums.append(float(item))
                else:
                    return await _send_json(
                        send, 422, {"error": "array must contain numbers"}
                    )
            mean = calculate_mean(nums)
            return await _send_json(send, 200, {"result": mean})

    except Exception:
        await _send_json(send, 500, {"error": "Internal Server Error"})


if __name__ == "__main__":
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
