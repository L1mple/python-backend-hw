from typing import Any, Awaitable, Callable, List
from http import HTTPStatus
from json import dumps, loads
from json.decoder import JSONDecodeError
from math import factorial

def fibonacci(n: int) -> int:
    if n < 2:
        return n
    a = 0
    b = 1
    for i in range(2, n + 1):
        a, b = b, a + b
    return b

def mean(numbers: List[float]) -> float:
    return sum(numbers) / len(numbers)

async def return_ok(send: Callable[[dict[str, Any]], Awaitable[None]],
                    payload_bytes: bytes) -> None:
    #code 200
    await send({
        "type": "http.response.start",
        "status": HTTPStatus.OK,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({"type": "http.response.body", "body": payload_bytes})

async def return_bad_request(send: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
    #code 400
    await send({
        "type": "http.response.start",
        "status": HTTPStatus.BAD_REQUEST,
        "headers": [(b"content-type", b"text/plain")],
    })
    await send({"type": "http.response.body", "body": b"Bad Request"})

async def return_not_found(send: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
    #code 404
    await send({
        "type": "http.response.start",
        "status": HTTPStatus.NOT_FOUND,
        "headers": [(b"content-type", b"text/plain")],
    })
    await send({"type": "http.response.body", "body": b"Not Found"})

async def return_unprocessable_entity(send: Callable[[dict[str, Any]], Awaitable[None]]) -> None:
    #code 422
    await send({
        "type": "http.response.start",
        "status": HTTPStatus.UNPROCESSABLE_ENTITY,
        "headers": [(b"content-type", b"text/plain")],
    })
    await send({"type": "http.response.body", "body": b"Unprocessable Entity"})


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
    # TODO: Ваша реализация здесь

    scope_type = scope.get("type")


    if scope_type == "lifespan":
        while True:
            event = await receive()
            if event["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif event["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
        return

    if scope_type != "http":
        return

    method = scope.get("method", "GET")
    path = scope.get("path", "/")


    if method == "GET":
        if "fibonacci" in path:
            parts = path.split("/")
            if len(parts) == 3 and parts[:2] == ["", "fibonacci"]:
                try:
                    n = int(parts[2])
                except ValueError:
                    await return_unprocessable_entity(send)
                    return

                if n < 0:
                    await return_bad_request(send)
                    return

                result = fibonacci(n)
                payload = dumps({"result": result}).encode()

                await return_ok(send, payload)
                return

        if path == "/factorial":
            query_string = scope["query_string"].decode()
            parts = query_string.split("=")
            if len(parts) == 2 and parts[0] == "n":
                try:
                    n = int(parts[1])
                except ValueError:
                    await return_unprocessable_entity(send)
                    return

                if n < 0:
                    await return_bad_request(send)
                    return

                result = factorial(n)
                payload = dumps({"result": result}).encode()

                await return_ok(send, payload)
                return

            await return_unprocessable_entity(send)
            return

        if path == "/mean":
            body = b""
            while True:
                event = await receive()
                if event["type"] == "http.request":
                    body += event.get("body", b"")
                    if not event.get("more_body", False):
                        break

            try:
                body = loads(body.decode())
            except JSONDecodeError:
                await return_unprocessable_entity(send)
                return

            if not isinstance(body, list):
                await return_unprocessable_entity(send)
                return

            if len(body) == 0:
                await return_bad_request(send)
                return

            if all(map(lambda x: isinstance(x, int) or isinstance(x, float), body)):
                numbers = body
                result = mean(numbers)
                payload = dumps({"result": result}).encode()
                await return_ok(send, payload)
                return

            await return_unprocessable_entity(send)
            return

    await return_not_found(send)
    return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
