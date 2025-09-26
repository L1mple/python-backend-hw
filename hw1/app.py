import json
import re
import math
from http import HTTPStatus
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

    async def send_start(status: int):
        await send(
            {"type": "http.response.start", "status": status, "headers": [[b"content-type", b"application/json"]]}
        )

    async def send_body(message: str, result: Any = None):
        body = {"message": message, "result": result}
        await send({"type": "http.response.body", "body": json.dumps(body).encode()})

    def decode_int(s: bytes | None):
        if not s:
            return None
        try:
            return int(s.decode())
        except Exception:
            return None

    try:
        path: str = scope["path"]

        if path == "/factorial":
            qs: dict[bytes, bytes] = {k: v[0] for k, v in parse_qs(scope["query_string"]).items()}
            n = decode_int(qs.get(b"n"))
            if n is None:
                await send_start(HTTPStatus.UNPROCESSABLE_ENTITY)
                await send_body("invalid query params")
                return
            if n < 0:
                await send_start(HTTPStatus.BAD_REQUEST)
                await send_body("n should be >= 0")
                return

            await send_start(HTTPStatus.OK)
            res = math.factorial(n)
            await send_body("success", str(res))

        elif path.startswith("/fibonacci"):
            params = path.split("/")[1:]
            if len(params) != 2:
                await send_start(HTTPStatus.BAD_REQUEST)
                await send_body("bad request")
                return

            if not re.fullmatch(r"-?\d+", params[1]):
                await send_start(HTTPStatus.UNPROCESSABLE_ENTITY)
                await send_body("n should be a digit")
                return

            n = int(params[1])
            if n < 0:
                await send_start(HTTPStatus.BAD_REQUEST)
                await send_body("n should be >= 0")
                return

            await send_start(HTTPStatus.OK)
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            await send_body("success", str(b))

        elif path == "/mean":
            body: bytes = b""
            more_body = True
            while more_body:
                message = await receive()
                if message["type"] != "http.request":
                    continue
                body += message.get("body", b"")
                more_body = message.get("more_body", False)
            args = json.loads(body.decode())

            if args is None:
                await send_start(HTTPStatus.UNPROCESSABLE_ENTITY)
                await send_body("should be array of floats")
                return

            if len(args) == 0:
                await send_start(HTTPStatus.BAD_REQUEST)
                await send_body("array should not be empty")
                return

            await send_start(HTTPStatus.OK)
            await send_body("success", sum(args) / len(args))

        else:
            await send_start(HTTPStatus.NOT_FOUND)
            await send_body("Not found")

    except Exception as e:
        error_text = f"Internal server error: {e}"
        await send_start(HTTPStatus.INTERNAL_SERVER_ERROR)
        await send_body(error_text)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
