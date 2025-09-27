import ast
import http.client
import math
from typing import Any, Awaitable, Callable


async def compute_fibonacci(num: int) -> int:
    start = [0, 1]
    for i in range(2, num + 1):
        start.append(start[i - 1] + start[i - 2])
    return start[num]


async def compute_factorial(num: int) -> int:
    return math.factorial(num)


async def compute_mean(values: list[float]) -> float:
    return sum(values) / len(values)


async def send_error(send: Callable[[dict[str, Any]], Awaitable[None]], status: int) -> None:
    await send({"type": "http.response.start", "status": status, "headers": []})
    await send({"type": "http.response.body", "body": b"Error"})


async def handle_lifespan(receive, send):
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
    """
    Args:
        scope: Словарь с информацией о запросе
        receive: Корутина для получения сообщений от клиента
        send: Корутина для отправки сообщений клиенту
    """
    if scope["type"] == "lifespan":
        await handle_lifespan(receive, send)

    if scope["path"].startswith("/fibonacci/"):
        await receive()
        path: str = scope["path"]
        path = path.rpartition("/")[2]
        try:
            num = int(path)
        except ValueError:
            await send_error(send, http.client.UNPROCESSABLE_ENTITY)
            return
        if num < 0:
            await send_error(send, http.client.BAD_REQUEST)
            return
        result = await compute_fibonacci(num)
        await send({"type": "http.response.start", "status": 200, "headers": [[b"content-type", b"application/json"]]})
        await send({"type": "http.response.body", "body": f'{{"result": {result}}}'.encode()})
        return

    if scope["path"] == "/factorial":
        await receive()
        query_string = scope["query_string"].decode()
        if not query_string or "n=" not in query_string:
            await send_error(send, http.client.UNPROCESSABLE_ENTITY)
            return
        num_str = query_string.rpartition("=")[2]
        if not num_str:
            await send_error(send, http.client.UNPROCESSABLE_ENTITY)
            return
        try:
            num = int(num_str)
        except ValueError:
            await send_error(send, http.client.UNPROCESSABLE_ENTITY)
            return
        if num < 0:
            await send_error(send, http.client.BAD_REQUEST)
            return
        result = await compute_factorial(num)
        await send({"type": "http.response.start", "status": 200, "headers": [[b"content-type", b"application/json"]]})
        await send({"type": "http.response.body", "body": f'{{"result": {result}}}'.encode()})
        return

    if scope["path"] == "/mean":
        body = await receive()
        body_str = body["body"].decode()
        if not body_str:
            await send_error(send, http.client.UNPROCESSABLE_ENTITY)
            return
        try:
            lst = ast.literal_eval(body_str)
        except (ValueError, SyntaxError):
            await send_error(send, http.client.UNPROCESSABLE_ENTITY)
            return
        if not isinstance(lst, list):
            await send_error(send, http.client.UNPROCESSABLE_ENTITY)
            return
        if len(lst) == 0:
            await send_error(send, http.client.BAD_REQUEST)
            return
        result = await compute_mean(lst)
        await send({"type": "http.response.start", "status": 200, "headers": [[b"content-type", b"application/json"]]})
        await send({"type": "http.response.body", "body": f'{{"result": {result}}}'.encode()})
        return
    await receive()
    await send_error(send, http.client.NOT_FOUND)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
