from typing import Any, Awaitable, Callable
import urllib.parse
import math

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
    
    assert scope["type"] == "http"

    path = scope["path"]
    query = urllib.parse.parse_qs(scope["query_string"].decode())

    status = 200
    body = b""
    try:
        if path == "/factorial":
            n = int(query.get("n", [0])[0])
            if n < 0:
                raise ValueError("n must be >= 0")
            result = math.factorial(n)
            body = str(result).encode()

        elif path.startswith("/fibonacci"):
            parts = path.strip("/").split("/")
            if len(parts) == 2:  # /fibonacci/<n>
                try:
                    n = int(parts[1])
                except ValueError:
                    raise ValueError("n must be an integer")
            else:
                # fallback to query string: /fibonacci?n=10
                n = int(query.get("n", [0])[0])

            if n < 0:
                raise ValueError("n must be >= 0")
            fib = [0, 1]
            for _ in range(2, n):
                fib.append(fib[-1] + fib[-2])
            body = str(fib[:n]).encode()

        elif path == "/mean":
            numbers_str = query.get("numbers", [""])[0]
            numbers = [float(v) for v in numbers_str.split(",") if v.strip()]
            if not numbers:
                raise ValueError("No numbers provided")
            result = sum(numbers) / len(numbers)
            body = str(result).encode()

        else:
            status = 404
            body = b"Not found"

    except Exception as e:
        status = 400
        body = f"Error: {str(e)}".encode()

    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [(b"content-type", b"text/plain")],
        }
    )
    await send({"type": "http.response.body", "body": body})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
