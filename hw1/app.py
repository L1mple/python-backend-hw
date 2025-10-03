from typing import Any, Awaitable, Callable
from http import HTTPStatus
import json

async def respond(code: int, body: bytes, send: Callable[[dict[str, Any]], Awaitable[None]]):
    await send({
        "type": "http.response.start",
        "status": code,
        "headers": [
            [b"content-type", b"application/json"],
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body,
    })

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
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return
    else:
        assert scope["type"] == "http"
    path = scope["path"]
    match path:
        case "/factorial":
            try:
                n = int(scope["query_string"].decode().replace("n=", ""))
            except ValueError:
                return await respond(HTTPStatus.UNPROCESSABLE_ENTITY, b"", send)

            if n < 0:
                return await respond(HTTPStatus.BAD_REQUEST, b"", send)

            factorial = 1
            for i in range(2, n + 1):
                factorial *= i

            return await respond(
                HTTPStatus.OK,
                bytes(json.dumps({"result":factorial}).encode("utf-8")),
                send,
            )
        case p if p.startswith("/fibonacci/"):
            try:
                n = int(path.removeprefix("/fibonacci/"))
            except ValueError:
                return await respond(HTTPStatus.UNPROCESSABLE_ENTITY, b"", send)
            
            if n < 0:
                return await respond(HTTPStatus.BAD_REQUEST, b"", send)

            a, b = 0, 1
            for _ in range(n): a, b = b, a+b
            return await respond(
                HTTPStatus.OK,
                bytes(json.dumps({"result":a}).encode("utf-8")),
                send,
            )
        case "/mean":
            body = b''
            event = await receive()
            if event['type'] == 'http.request':
                body = event['body']
            match json.loads(body.decode()):
                case None:
                    return await respond(HTTPStatus.UNPROCESSABLE_ENTITY, b"", send)
                case b if len(b) == 0:
                    return await respond(HTTPStatus.BAD_REQUEST, b"", send)
                case b:
                    mean = sum(b) / len(b)
                    return await respond(
                        HTTPStatus.OK,
                        bytes(json.dumps({"result":mean}).encode("utf-8")),
                        send,
                    )
        case _:
            return await respond(HTTPStatus.NOT_FOUND, b"", send)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
