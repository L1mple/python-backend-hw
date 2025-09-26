from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import json

from utils import fibonacci, factorial, mean

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
    if scope.get("type") == "lifespan":
        while True:
            message = await receive()
            if message.get("type") == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message.get("type") == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return

    path = scope["path"]
    query = parse_qs(scope["query_string"].decode())
    method = scope.get("method", "GET")

    def json_response(data: dict, status_code: int = 200):
        return json.dumps(data).encode(), b"application/json", status_code

    if path == "/factorial" and method == "GET":
        n_raw = query.get("n", [None])[0]
        if not n_raw:
            body, content_type, status = json_response({"detail": "Missing or empty 'n' parameter"}, 422)
        else:
            try:
                n = int(n_raw)
            except Exception:
                body, content_type, status = json_response({"detail": "'n' must be an integer"}, 422)
            else:
                if n < 0:
                    body, content_type, status = json_response({"detail": "'n' must be >= 0"}, 400)
                else:
                    body, content_type, status = json_response({"result": factorial(n)})

    elif path.startswith("/fibonacci") and method == "GET":
        parts = path.split("/")
        n_raw = parts[2] if len(parts) > 2 else ""
        if not n_raw:
            body, content_type, status = json_response({"detail": "Missing or empty n parameter"}, 422)
        else:
            try:
                n = int(n_raw)
            except Exception:
                body, content_type, status = json_response({"detail": "n must be integer"}, 422)
            else:
                if n < 0:
                    body, content_type, status = json_response({"detail": "n must be >= 0"}, 400)
                else:
                    body, content_type, status = json_response({"result": fibonacci(n)})

    elif path == "/mean" and method == "GET":
        raw_body = scope.get("body", b"")
        while True:
            message = await receive()
            if message["type"] == "http.request":
                raw_body += message.get("body", b"")
                if not message.get("more_body", False):
                    break
        try:
            body_data = json.loads(raw_body.decode()) if raw_body else None
        except Exception:
            body_data = None

        if body_data is None:
            body, content_type, status = json_response({"detail": "Missing or invalid body"}, 422)
        elif not isinstance(body_data, list) or not body_data:
            body, content_type, status = json_response({"detail": "Body must be non-empty list"}, 400)
        else:
            try:
                numbers = [float(x) for x in body_data]
            except Exception:
                body, content_type, status = json_response({"detail": "All elements must be numbers"}, 400)
            else:
                body, content_type, status = json_response({"result": mean(",".join(str(x) for x in numbers))})

    else:
        body, content_type, status = json_response({"detail": "Not Found"}, 404)

    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [[b"content-type", content_type]]
    })

    await send({
        "type": "http.response.body",
        "body": body
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
