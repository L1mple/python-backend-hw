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

    if scope["type"] == "lifespan":
        await handle_lifespan(scope, receive, send)
        return
        
    if scope["type"] != "http":
        return
        
    await handle_http_request(scope, receive, send)


async def handle_lifespan(scope, receive, send):
    """Обработка событий жизненного цикла приложения"""
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            return
            

async def handle_http_request(scope, receive, send):
    """Обработка HTTP запроса"""
    method = scope["method"]
    path = scope["path"]
    query_string = scope["query_string"].decode()

    status, result = await process_route(path, query_string, receive)
    
    headers = [(b"content-type", b"application/json")]
    response_body = json.dumps(result).encode()

    await send({
        "type": "http.response.start", 
        "status": status, 
        "headers": headers
    })
    await send({
        "type": "http.response.body", 
        "body": response_body
    })


async def process_route(path: str, query_string: str, receive) -> tuple[int, dict]:

    status = 200
    result: dict[str, Any] = {}

    try:
        if path == "/factorial":
            return await handler_factorial(query_string)
        
        elif path.startswith("/fibonacci/"):
            return await handler_fibonacci(path)

        elif path == "/mean":
            return await handler_mean(receive, query_string)

        else:
            status = 404
            result = {"error": "Unknown path"}
    except ValueError as e:
            status = getattr(e, 'status_code', 400)
            return status, {"error": str(e)}
    except Exception as e:
        result = {"error": f"Error: {e}"}

    return status, result


async def handler_factorial(query_string):
    params = parse_qs(query_string)
    
    if "n" not in params or params["n"][0] == "":
        error = ValueError("Missing parameter 'n'")
        error.status_code = 422
        raise error
        
    try:
        n = int(params["n"][0])
    except ValueError:
        error = ValueError("Parameter 'n' must be an integer")
        error.status_code = 422
        raise error
        
    if n < 0:
        error = ValueError("n must be >= 0")
        error.status_code = 400
        raise error

    return 200, {"result": get_factorial(n)}


async def handler_fibonacci(path):
    match = re.fullmatch(r"/fibonacci/(-?\d+)", path)
    if not match:
        error = ValueError("Missing parameter 'n' or value is not a numerical value")
        error.status_code = 422
        raise error
        
    n = int(match.group(1))

    if n < 0:
        error = ValueError("n must be >= 0")
        error.status_code = 400
        raise error

    return 200, {"result": get_fibonacci(n)}

    
async def handler_mean(receive, query_string):
    data = None
    message = await receive()
    body_bytes = message.get("body", b"")

    if not body_bytes:
        params = parse_qs(query_string)
        if "numbers" in params or params["numbers"][0]:
            try:
                numbers_str = params["numbers"][0]
                data = [float(x.strip()) for x in numbers_str.split(",")]
            except ValueError:
                error = ValueError("Parameter 'numbers' must be comma-separated numbers")
                error.status_code = 422
                raise error
        else:
            error = ValueError("Missing request body or numbers parameter")
            error.status_code = 422
            raise error
            
    else: 
        try:
            data = json.loads(body_bytes)
        except json.JSONDecodeError:
            error = ValueError("Request body must be a valid JSON")
            error.status_code = 422
            raise error

    if not isinstance(data, list):
        error = ValueError("Data must be a list")
        error.status_code = 422
        raise error

    if not data:
        error = ValueError("List is empty")
        error.status_code = 400
        raise error
    
    if not all(isinstance(x, (int, float)) for x in data):
        error = ValueError("List must contain only numbers")
        error.status_code = 400
        raise error

    return 200, {"result": get_mean(data)}


def get_factorial(n: int) -> int:
    if n == 0:
        return 1
    res = 1
    for i in range(2, n + 1):
        res *= i
    return res

def get_fibonacci(n: int) -> int:
    if n == 0:
        return 0
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b

def get_mean(data: list[float]) -> float:
    return sum(data) / len(data)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
