from http import HTTPStatus
from typing import Any, Awaitable, Callable

from routes.fibonacci import handle_fibonacci
from routes.factorial import handle_factorial
from routes.mean import handle_mean

from helpers import send_json


ROUTES = {
    ("GET", "/factorial"): handle_factorial,
    ("GET", "/mean"): handle_mean,
}

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
    
    if scope["type"] != "http":
        return

    method: str = scope["method"]
    path: str = scope["path"]

    # Сначала проверяем точные маршруты
    handler = ROUTES.get((method, path))
    if handler is not None:
        await handler(scope, receive, send)
        return

    # Проверяем маршруты с параметрами
    if method == "GET" and path.startswith("/fibonacci/"):
        await handle_fibonacci(scope, receive, send)
        return

    return await send_json(send, HTTPStatus.NOT_FOUND, f"Not Found: {method} {path}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
