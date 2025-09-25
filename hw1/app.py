from enum import Enum
import json
from typing import Any, Awaitable, Callable
from http import HTTPStatus

from endpoints import mean, process_factorial, process_fibonacci

def send_response_start(status_code: int, body_str: str):
    response_body = body_str.encode("utf-8")
    return {
        "type": "http.response.start",
        "status": status_code,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(response_body)).encode()],
        ],
    }

def send_response_body(body_str: str):
    return {
        "type": "http.response.body",
        "body": body_str.encode("utf-8"),
    }

async def handle_lifespan(receive: Callable, send: Callable):
    while True:
        message = await receive()
        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            break

async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    if scope["type"] == "lifespan":
        await handle_lifespan(receive, send)
        return

    if scope["type"] != "http":
        return

    method = scope["method"]
    path = scope["path"]

    code = HTTPStatus.OK
    body = ""

    if method != "GET":
        code = HTTPStatus.NOT_FOUND
        body = json.dumps({"error": "Not found"})
    else:
        if path == "/factorial":
            code, body = process_factorial(scope["query_string"]) 
        elif path.startswith("/fibonacci/"):
             code, body = process_fibonacci(path)   
        elif path == "/mean":
            message = await receive()
            request_body = json.loads(message['body'])
            try:
                request_body = list(request_body)
                if len(request_body) == 0:
                    code = HTTPStatus.BAD_REQUEST
                else:
                    body = json.dumps({"result": mean(request_body)})
            except TypeError:
                code = HTTPStatus.UNPROCESSABLE_ENTITY
        else:
            code = HTTPStatus.NOT_FOUND
            body = json.dumps({"error": "Invalid number"})
            

    await send(send_response_start(code, body))
    await send(send_response_body(body))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
