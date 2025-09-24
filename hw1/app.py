from typing import Any, Awaitable, Callable
import urllib.parse
import math
import json
from http import HTTPStatus

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
    
    #assert scope["type"] == "http"

    if scope["type"] == "lifespan":
        # Ждём события запуска/остановки
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    elif scope["type"] == "http":
        method = scope["method"]
        path = scope["path"]
        query = urllib.parse.parse_qs(scope["query_string"].decode())

        status = HTTPStatus.OK
        response: dict[str, Any] = {}

        try:
            # ---------- /factorial?n=5 ----------
            if path == "/factorial":
                if "n" not in query or query["n"][0] == "":
                    status = HTTPStatus.UNPROCESSABLE_ENTITY
                    raise ValueError("Missing n")
                try:
                    n = int(query["n"][0])
                except ValueError:
                    status = HTTPStatus.UNPROCESSABLE_ENTITY
                    raise ValueError("Invalid n")
                if n < 0:
                    status = HTTPStatus.BAD_REQUEST
                    raise ValueError("n must be >= 0")
                response = {"result": math.factorial(n)}

            # ---------- /fibonacci/{n} ----------
            elif path.startswith("/fibonacci"):
                parts = path.split("/")
                if len(parts) != 3 or not parts[2]:
                    status = HTTPStatus.UNPROCESSABLE_ENTITY
                    raise ValueError("Missing n in path")
                try:
                    n = int(parts[2])
                except ValueError:
                    status = HTTPStatus.UNPROCESSABLE_ENTITY
                    raise ValueError("Invalid path parameter")
                if n < 0:
                    status = HTTPStatus.BAD_REQUEST
                    raise ValueError("n must be >= 0")
                fib = [0, 1]
                for _ in range(2, n):
                    fib.append(fib[-1] + fib[-2])
                response = {"result": fib[:n]}

            # ---------- /mean ----------
            elif path == "/mean":
                numbers = None

                # 1. Пробуем из query (?numbers=1,2,3)
                if "numbers" in query:
                    try:
                        numbers = [
                            float(v) for v in query["numbers"][0].split(",") if v.strip()
                        ]
                    except Exception:
                        status = HTTPStatus.UNPROCESSABLE_ENTITY
                        raise ValueError("Invalid numbers in query")

                # 2. Если в query нет, читаем body (JSON)
                if numbers is None:
                    body_bytes = b""
                    more_body = True
                    while more_body:
                        message = await receive()
                        body_bytes += message.get("body", b"")
                        more_body = message.get("more_body", False)

                    if not body_bytes:
                        status = HTTPStatus.UNPROCESSABLE_ENTITY
                        raise ValueError("Missing body")

                    try:
                        data = json.loads(body_bytes.decode())
                    except Exception:
                        status = HTTPStatus.UNPROCESSABLE_ENTITY
                        raise ValueError("Invalid JSON")

                    numbers = data if isinstance(data, list) else data.get("numbers")

                # Валидации
                if not isinstance(numbers, list) or not all(
                    isinstance(v, (int, float)) for v in numbers
                ):
                    status = HTTPStatus.BAD_REQUEST
                    raise ValueError("numbers must be a list of numbers")
                if not numbers:
                    status = HTTPStatus.BAD_REQUEST
                    raise ValueError("No values provided")

                result = sum(numbers) / len(numbers)
                response = {"result": result}

            else:
                status = HTTPStatus.NOT_FOUND
                response = {"error": "Not found"}

        except Exception as e:
            if not response:
                response = {"error": str(e)}

        body = json.dumps(response).encode()

        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
