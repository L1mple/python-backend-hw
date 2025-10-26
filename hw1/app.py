import json
from math import factorial
from typing import Any, Awaitable, Callable


def fibonacci(n: int):
    if n < 0:
        raise ValueError(f"Expected parameter n must be non-negative. Got n={n}")

    if n == 0:
        return 0

    first_value, second_value = 0, 1

    for i in range(n - 1):
        first_value, second_value = second_value, first_value + second_value

    return second_value


async def send_response(
    response_status_code: int,
    response_content_type: bytes,
    response_body: bytes,
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    await send(
        {
            "type": "http.response.start",
            "status": response_status_code,
            "headers": [
                [b"content-type", response_content_type],
            ],
        }
    )
    await send({"type": "http.response.body", "body": response_body})


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
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                break

    elif scope["type"] == "http":
        path = scope["path"]

        if path == "/" or path == "/not_found":
            await send_response(404, b"text/plain", b"not found", send)

        elif path == "/factorial":
            try:
                n = int(scope["query_string"].decode().replace("n=", ""))
                if n < 0:
                    await send_response(
                        400,
                        b"text/plain",
                        b"Invalid value for n, must be non-negative",
                        send,
                    )
                else:
                    result = factorial(n)
                    response_body = bytes(
                        json.dumps({"result": result}), encoding="utf-8"
                    )
                    await send_response(200, b"application/json", response_body, send)
            except ValueError:
                await send_response(422, b"text/plain", b"unprocessible entity", send)

        elif path.startswith("/fibonacci/"):
            try:
                n = int(path.split("/")[2])
                if n < 0:
                    await send_response(
                        400,
                        b"text/plain",
                        b"Invalid value for n, must be non-negative",
                        send,
                    )
                else:
                    result = fibonacci(n)
                    response_body = bytes(
                        json.dumps({"result": result}), encoding="utf-8"
                    )
                    await send_response(200, b"application/json", response_body, send)
            except ValueError:
                await send_response(422, b"text/plain", b"unprocessible entity", send)

        elif path == "/mean":
            body = b""
            event = await receive()
            if event["type"] == "http.request":
                body = event.get("body", b"")
            inp_arr = json.loads(body.decode())
            if inp_arr is None:
                await send_response(422, b"text/plain", b"unprocessible entity", send)
            else:
                if len(inp_arr) == 0:
                    await send_response(
                        400,
                        b"text/plain",
                        b"Invalid value for body, must be non-empty array of floats",
                        send,
                    )
                else:
                    result = sum(inp_arr) / len(inp_arr)
                    response_body = bytes(
                        json.dumps({"result": result}), encoding="utf-8"
                    )
                    await send_response(200, b"application/json", response_body, send)
        else:
            await send_response(422, b"text/plain", b"unprocessible entity", send)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
