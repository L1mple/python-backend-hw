from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import math
import json

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
        return

    if scope["type"] == "http":
        path = scope['path']
        if path == '/factorial':
            query_string = scope["query_string"].decode("utf-8")
            params = parse_qs(query_string)
            if "n" not in params or not params["n"][0]:
                await send_error(send, 422, "Missing or empty parameter n")
                return
            try:
                n = int(params["n"][0])
            except (ValueError, TypeError):
                await send_error(send, 422, "n must be an integer")
                return
            if n < 0:
                await send_error(send, 400, "n must be non-negative")
                return
            
            result = math.factorial(int(params["n"][0]))
            response = json.dumps({"result": result})

            await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"content-type", b"application/json"]
                    ],
                })
            await send({
                    "type": "http.response.body",
                    "body": response.encode("utf-8"),
                })            

        elif path == '/mean':
            body = b""
            while True:
                message = await receive()
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    break
            
            if not body:
                await send_error(send, 422, "No JSON given")
                return
            try:
                text = body.decode("utf-8")
                data = json.loads(text)
            except Exception:
                await send_error(send, 422, "Invalid JSON")
                return


            if data is None:
                await send_error(send, 422, "No JSON given")
                return
            if not isinstance(data, list):
                await send_error(send, 400, "Data must be a list")
                return
            if len(data) == 0:
                await send_error(send, 400, "Empty list")
                return
            elif not all(isinstance(x, (int, float)) for x in data):
                await send_error(send, 400, "All elements must be numbers")
                return
            else:
                result = sum(data)/len(data)
                response = json.dumps({"result": result})

                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [
                        [b"content-type", b"application/json"]
                    ],
                })
                await send({
                    "type": "http.response.body",
                    "body": response.encode("utf-8"),
                })


        elif path.startswith('/fibonacci/'):
            parts = path.split('/')
            if len(parts) != 3 or not parts[2]:
                await send_error(send, 422, "Invalid path parameter")
                return
            n_str = parts[2]
            try:
                n = int(n_str)
            except ValueError:
                await send_error(send, 422, "n must be an integer")
                return
            if n < 0:
                await send_error(send, 400, "n must be non-negative")
                return

            def fib(n):
                a, b = 0, 1
                for _ in range(n):
                    a, b = b, a + b
                return a

            result = fib(n)
            response = json.dumps({"result": result})

            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", b"application/json"]
                ],
            })
            await send({
                "type": "http.response.body",
                "body": response.encode("utf-8"),
            })
            return

        else:
            await send_error(send, 404, "There's no endpoint like that")
            return

async def send_error(send, status: int, message: str = ""):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"text/plain; charset=utf-8"]
        ],
    })
    await send({
        "type": "http.response.body",
        "body": message.encode("utf-8"),
    })

    


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
