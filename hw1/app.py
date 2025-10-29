from typing import Any, Awaitable, Callable

import json  # https://docs.python.org/3/library/json.html - это стандартная библиотека в составе python (я не хочу делать алгос по десериализации JSON)


# Числовые коды (если нельзя использовать http.HTTPStatus)
OK, BAD_REQUEST, NOT_FOUND, UNPROC = 200, 400, 404, 422


# Специальные исключения
class ENotFound(Exception): ...


class EBadRequest(Exception): ...


# --- helpers & math -----------------------------------------------------------
def read_query(qs: bytes) -> dict[str, str]:
    """Вместо urllib вот такая заглушка"""
    if not qs:
        return {}
    out: dict[str, str] = {}
    s = qs.decode()
    for pair in s.split("&"):
        if not pair:
            continue
        k, v = (pair.split("=", 1) + [""])[:2]
        out[k] = v
    return out


def factorial(n: int) -> int:
    """Факториал"""
    r = 1
    for i in range(2, n + 1):
        r *= i
    return r


def fibonacci(n: int) -> int:
    """Фибоначчи"""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def mean(nums: list[float]) -> float:
    """Среднее"""
    return sum(nums) / len(nums)


async def read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    """
    Args:
        receive: Корутина для получения сообщений от клиента
    """
    body = b""
    while True:
        msg = await receive()
        if msg["type"] == "http.request":
            body += msg.get("body", b"")
            if not msg.get("more_body"):
                break
        else:
            break
    return body


async def respond(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    data: Any | None = None,
):
    """
    Args:
        send: Словарь с информацией о запросе
        status: статус код
        data: любая инфа, которую в байтах хотим закинуть
    """
    if data is None:
        headers = [(b"content-type", b"text/plain"), (b"content-length", b"0")]
        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        await send({"type": "http.response.body", "body": b""})
    else:
        body = json.dumps({"result": data}).encode()
        headers = [
            (b"content-type", b"application/json"),
            (b"content-length", str(len(body)).encode()),
        ]
        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        await send({"type": "http.response.body", "body": body})


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
    # По поводу lifespan: https://www.youtube.com/watch?v=VJ963Z6lsQ4
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            t = message.get("type")
            if t == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif t == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    if scope["type"] != "http":
        return

    method, path = scope["method"], scope["path"]
    body = await read_body(receive)

    try:
        if method != "GET":
            raise ENotFound()

        # /factorial?n=...
        if path == "/factorial":
            n_raw = read_query(scope.get("query_string", b"")).get("n")
            if n_raw is None:
                raise ValueError("missing n")  # -> 422
            n = int(n_raw)  # ValueError -> 422
            if n < 0:
                raise EBadRequest()  # -> 400
            return await respond(send, OK, factorial(n))

        # /fibonacci/{n}
        if path.startswith("/fibonacci/"):
            tail = path.split("/", 2)[2]
            n = int(tail)  # ValueError -> 422
            if n < 0:
                raise EBadRequest()  # -> 400
            return await respond(send, OK, fibonacci(n))

        # /mean (GET body = JSON array)
        if path == "/mean":
            if not body:
                raise ValueError("empty body")  # -> 422
            data = json.loads(body.decode())  # JSONDecodeError -> 422
            if not isinstance(data, list):
                raise ValueError("not a list")  # -> 422
            if not data:
                raise EBadRequest()  # -> 400
            nums = [float(x) for x in data]  # ValueError/TypeError -> 422
            return await respond(send, OK, mean(nums))

        raise ENotFound()

    except ENotFound:
        return await respond(send, NOT_FOUND)
    except EBadRequest:
        return await respond(send, BAD_REQUEST)
    except (ValueError, TypeError, json.JSONDecodeError):
        return await respond(send, UNPROC)
    except Exception:
        # На всякий случай — считаем прочие сбои как 400
        return await respond(send, BAD_REQUEST)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
