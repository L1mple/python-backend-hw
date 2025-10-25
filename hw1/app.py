import json
import math
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
    if scope["type"] != "http":
        await send({
            "type": "http.response.start",
            "status": 422,
            "headers": [[b"content-type", b"application/json"]],
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps({"error": "Unprocessable Entity"}).encode(),
        })
        return
    
    method = scope["method"]
    path = scope["path"]
    query_string = scope.get("query_string", b"").decode()

    if method != "GET":
        await send({
            "type": "http.response.start",
            "status": 404,
            "headers": [[b"content-type", b"application/json"]],
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps({"error": "Not Found"}).encode(),
        })
        return
    
    try:
        if path.startswith("/fibonacci"):
            try:
                n = int(path.split("/fibonacci/")[1])
            except (ValueError, IndexError):
                await send_error(send, 422, "Unprocessable Entity")
                return
            
            if n < 0:
                await send_error(send, 400, "Invalid value for n, must be non-negative")
                return
            a, b = 0, 1
            for _ in range(n):
                a, b = b, a + b
            
            await send_success(send, a)
            return
        elif path.startswith("/factorial"):
            params = parse_qs(query_string)
            
            if "n" not in params:
                await send_error(send, 422, "Unprocessable Entity")
                return
            
            try:
                n_value = params["n"][0]
                if n_value == "":
                    await send_error(send, 422, "Unprocessable Entity")
                    return
                n = int(n_value)
            except (ValueError, IndexError):
                await send_error(send, 422, "Unprocessable Entity")
                return
            
            if n < 0:
                await send_error(send, 400, "Invalid value for n, must be non-negative")
                return
            
            result = math.factorial(n)
            await send_success(send, result)
            return

        elif path.startswith("/mean"):
            body = b""
            while True:
                message = await receive()
                if message["type"] == "http.request":
                    body += message.get("body", b"")
                    if not message.get("more_body", False):
                        break
                elif message["type"] == "http.disconnect":
                    return
                
            if not body:
                await send_error(send, 422, "Unprocessable Entity")
                return
            
            try:
                data = json.loads(body.decode())
                if not isinstance(data, list):
                    await send_error(send, 422, "Unprocessable Entity")
                    return
                if len(data) == 0:
                    await send_error(send, 400, "Empty list provided")
                    return
                numbers = [float(x) for x in data]
                
            except (json.JSONDecodeError, ValueError, TypeError):
                await send_error(send, 422, "Unprocessable Entity")
                return
            
            result = sum(numbers) / len(numbers)
            await send_success(send, result)
            return
        else:
            await send({
                "type": "http.response.start",
                "status": 404,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({
                "type": "http.response.body",
                "body": json.dumps({"error": "Not Found"}).encode(),
            })
            return
            
    except Exception as e:
        await send_error(send, 500, f"Internal server error: {str(e)}")


async def send_success(send: Callable[[dict[str, Any]], Awaitable[None]], result):
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [[b"content-type", b"application/json"]],
    })
    await send({
        "type": "http.response.body",
        "body": json.dumps({"result": result}).encode(),
    })


async def send_error(send: Callable[[dict[str, Any]], Awaitable[None]], status: int, message: str):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", b"application/json"]],
    })
    await send({
        "type": "http.response.body",
        "body": json.dumps({"error": message}).encode(),
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)