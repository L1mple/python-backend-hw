import math
import statistics
import json
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
from http import HTTPStatus


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    """
    Простейшее ASGI-приложение.
    Поддерживает три эндпоинта:
      - /factorial?n=5
      - /fibonacci?n=10
      - /mean?numbers=1&numbers=2&numbers=3
    """

    if scope["type"] != "http":
        return

    path = scope.get("path", "/")
    query_string = scope.get("query_string", b"").decode()
    params = parse_qs(query_string)

    # Хелпер для ответа
    async def send_response(status: int, data: dict):
        body = json.dumps(data).encode("utf-8")
        headers = [(b"content-type", b"application/json")]
        await send(
            {"type": "http.response.start", "status": status, "headers": headers}
        )
        await send({"type": "http.response.body", "body": body})

    try:
        if path == "/factorial":
            n = int(params.get("n", [None])[0])
            if n is None or n < 0 or n > 100:
                raise ValueError("n must be between 0 and 100")
            result = math.factorial(n)
            await send_response(HTTPStatus.OK, {"result": result})

        elif path == "/fibonacci":
            n = int(params.get("n", [None])[0])
            if n is None or n < 0 or n > 100:
                raise ValueError("n must be between 0 and 100")
            # классическая реализация
            a, b = 0, 1
            seq = []
            for _ in range(n):
                seq.append(a)
                a, b = b, a + b
            await send_response(HTTPStatus.OK, {"result": seq})

        elif path == "/mean":
            nums = params.get("numbers", None)
            if not nums:
                raise ValueError("numbers must be provided")
            numbers = [float(x) for x in nums]
            result = statistics.mean(numbers)
            await send_response(HTTPStatus.OK, {"result": result})

        else:
            await send_response(HTTPStatus.NOT_FOUND, {"detail": "Not Found"})

    except Exception as e:
        await send_response(HTTPStatus.BAD_REQUEST, {"detail": str(e)})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
