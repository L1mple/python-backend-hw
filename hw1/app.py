from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import json
import re


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    """
    ASGI-приложение с поддержкой:
        /factorial?n=5
        /fibonacci/10
        /mean?numbers=1,2,3
    
    Args:
        scope: Словарь с информацией о запросе
        receive: Корутина для получения сообщений от клиента
        send: Корутина для отправки сообщений клиенту
    """

    if scope["type"] != "http":
        return

    method = scope["method"]
    path = scope["path"]
    query_string = scope["query_string"].decode()

    status = 200
    headers = [(b"content-type", b"application/json")]
    result: dict[str, Any] = {}

    try:
        if path == "/factorial":         
            params = parse_qs(query_string)
            
            if "n" not in params or params["n"][0] == "":
                status = 422
                raise ValueError("Missing parameter 'n' or empty")
                
            try:
                n = int(params["n"][0])
            except ValueError:
                status = 422
                raise ValueError("Parameter 'n' must be an integer")
                
            if n < 0:
                status = 400
                raise ValueError("n must be >= 0")

            result["result"] = get_factorial(n)
        
        elif "/fibonacci" in path:
            match = re.fullmatch(r"/fibonacci/(-?\d+)", path)

            if not match:
                status = 422
                raise ValueError("Missing parameter 'n' or value is not a numerical value")
                
            n = int(match.group(1))
        
            if n < 0:
                status = 400
                raise ValueError("n must be >= 0")

            result["result"] = get_fibonacci(n)

        elif path == "/mean":
            params = parse_qs(query_string)
            data = None
            
            if "numbers" in params or params["numbers"][0]:
                try:
                    numbers_str = params["numbers"][0]
                    data = [float(x.strip()) for x in numbers_str.split(",")]
                except ValueError:
                    status = 422
                    raise ValueError("Parameter 'numbers' must be comma-separated numbers")
            else:
                message = await receive()
                body_bytes = message.get("body", b"")
                
                if not body_bytes:
                    status = 422
                    raise ValueError("Missing request body or numbers parameter")
                    
                try:
                    data = json.loads(body_bytes)
                except json.JSONDecodeError:
                    status = 422
                    raise ValueError("Request body must be a valid JSON")

            if not data:
                status = 400
                raise ValueError("List is empty")
            
            if not all(isinstance(x, (int, float)) for x in data):
                status = 400
                raise ValueError("List must contain only numbers")
        
            result["result"] = get_mean(data)

        else:
            status = 404
            result = {"error": "Unknown path"}

    except Exception as e:
        result = {"error": f"Error: {e}"}

    # Отправка ответа
    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": json.dumps(result).encode()})


def get_factorial(n: int) -> int:
    res = 1
    for i in range(2, n + 1):
        res *= i
    return res


def get_fibonacci(n: int) -> int:
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def get_mean(data: list[float]) -> float:
    return sum(data) / len(data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
