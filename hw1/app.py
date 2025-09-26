from typing import Any, Awaitable, Callable

from utils import handle_404
from math_handler import handle_factorial, handle_fibonacci, handle_mean


routes = {
    ("factorial", "GET"): handle_factorial,
    ("fibonacci", "GET"): handle_fibonacci,
    ("mean", "GET"): handle_mean,
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
                return

    if scope["type"] == "http":
        path = scope["path"].strip("/").split("/")
        for root, handler in routes.items():
            if path[0] == root[0] and scope["method"] == root[1]:
                await handler(scope, receive, send)
                return
        await handle_404(scope, receive, send)
        return

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
