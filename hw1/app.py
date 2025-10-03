from typing import Any, Awaitable, Callable

from utils import error_response
from handlers import handle_factorial, handle_fibonacci, handle_mean
    
ROUTES = {
    ('GET', '/factorial'): handle_factorial,
    ('GET', '/fibonacci'): handle_fibonacci,
    ('GET', '/mean'): handle_mean,
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
            
    if scope["type"] != "http":
        return
    
    path = scope['path']
    path_segments = path.strip("/").split('/', 1)
    normalized_path = '/' + path_segments[0] if path_segments[0] else '/'

    method = scope['method']

    handler = ROUTES.get((method, normalized_path))

    if handler:
        await handler(scope, receive, send)
    else:
        await error_response(send, 404, "Not Found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
