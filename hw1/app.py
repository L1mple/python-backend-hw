from typing import Any, Awaitable, Callable

from handlers import BaseHandler, FibonacciHandler, FactorialHandler, MeanHandler


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
            t = message.get("type")
            if t == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif t == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    if scope['type'] != 'http':
        return

    method = scope['method']
    path = scope['path']

    if method != 'GET':
        await BaseHandler.send_response(send, 404, {"error": "Not Found"})
        return

    if path.startswith('/fibonacci'):
        await FibonacciHandler.handle(path, send)
        return

    if path == '/factorial':
        query_string = scope.get('query_string', b'')
        await FactorialHandler.handle(query_string, send)
        return

    if path == '/mean':
        await MeanHandler.handle(receive, send)
        return

    await BaseHandler.send_response(send, 404, {"error": "Not Found"})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
