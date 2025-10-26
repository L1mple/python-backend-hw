from typing import Any, Awaitable, Callable
import json
import math
from urllib.parse import parse_qs
from http import HTTPStatus

async def _receive_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        if message["type"] != "http.request":
            break
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    return body


async def _send_json(send: Callable[[dict[str, Any]], Awaitable[None]], status: int, obj: dict):
    body = json.dumps(obj).encode("utf-8")
    headers = [
        (b"content-type", b"application/json"),
        (b"content-length", str(len(body)).encode("utf-8")),
    ]
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})


def _parse_query_string(query_string: bytes) -> dict[str, list[str]]:
    qs = query_string.decode("utf-8")
    return parse_qs(qs, keep_blank_values=True)


def _try_parse_int(value: str):
    if value == "":
        return None, "empty"
    try:
        iv = int(value)
        return iv, None
    except Exception:
        return None, "bad"


def _factorial(n: int) -> int:
    return math.factorial(n)


def _fibonacci(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    if scope.get("type") != "http":
        await _send_json(send, HTTPStatus.NOT_FOUND, {"detail": "Not found"})
        return

    method = scope.get("method", "")
    path = scope.get("path", "")

    if method != "GET":
        await _send_json(send, HTTPStatus.NOT_FOUND, {"detail": "Not found"})
        return


    if path == "/factorial":
        qs = _parse_query_string(scope.get("query_string", b""))
        if "n" not in qs:
            await _send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Missing 'n' parameter"})
            return
        n_raw = qs["n"][0]
        n_val, err = _try_parse_int(n_raw)
        if err is not None:
            await _send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Parameter 'n' must be an integer"})
            return
        if n_val < 0:
            await _send_json(send, HTTPStatus.BAD_REQUEST, {"detail": "n must be non-negative"})
            return
   
        try:
            res = _factorial(n_val)
        except (OverflowError, ValueError) as e:
            await _send_json(send, HTTPStatus.BAD_REQUEST, {"detail": str(e)})
            return
        await _send_json(send, HTTPStatus.OK, {"result": res})
        return


    if path.startswith("/fibonacci/"):
        n_raw = path[len("/fibonacci/") :]
        n_val, err = _try_parse_int(n_raw)
        if err is not None:
            await _send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Path parameter must be integer"})
            return
        if n_val < 0:
            await _send_json(send, HTTPStatus.BAD_REQUEST, {"detail": "n must be non-negative"})
            return
        res = _fibonacci(n_val)
        await _send_json(send, HTTPStatus.OK, {"result": res})
        return


    if path == "/mean":
        body = await _receive_body(receive)
        if not body:
            await _send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Missing JSON body"})
            return
        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            await _send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Invalid JSON"})
            return
        if not isinstance(payload, list):
            await _send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "JSON must be an array of numbers"})
            return
        if len(payload) == 0:
            await _send_json(send, HTTPStatus.BAD_REQUEST, {"detail": "Array must not be empty"})
            return
        nums = []
        for item in payload:
            if isinstance(item, (int, float)):
                nums.append(float(item))
            else:
                await _send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"detail": "Array elements must be numbers"})
                return
        mean_value = sum(nums) / len(nums)
        await _send_json(send, HTTPStatus.OK, {"result": mean_value})
        return

    await _send_json(send, HTTPStatus.NOT_FOUND, {"detail": "Not found"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)