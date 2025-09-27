from http import HTTPStatus
from json import dumps, loads
from re import Match, match
from typing import Any, Awaitable, Callable
from urllib import parse


class Handler:
    def __init__(self):
        self.re_map = {
            r"/fibonacci/(.+)?": self.fibonacci,
            r"/factorial/?": self.factorial,
            r"/mean/?": self.mean,
        }

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ):
        status = HTTPStatus.NOT_FOUND
        body = ""
        message = await receive()
        query = parse.parse_qs(scope["query_string"].decode())
        for pattern, handler in self.re_map.items():
            path = match(pattern, scope["path"])
            if path:
                status, body = await handler(path, query, message["body"].decode())

        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": {},
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body.encode(),
            }
        )

    async def fibonacci(
        self, path: Match, query: dict[str, Any], payload: str
    ) -> tuple[HTTPStatus, str]:
        try:
            n = int(path.group(1))
        except ValueError:
            return HTTPStatus.UNPROCESSABLE_ENTITY, ""
        if n < 0:
            return HTTPStatus.BAD_REQUEST, ""
        fib = 1
        while n > 0:
            fib += fib
            n -= 1
        return HTTPStatus.OK, dumps({"result": fib})

    async def factorial(
        self, path: Match, query: dict[str, Any], payload: str
    ) -> tuple[HTTPStatus, str]:
        if "n" not in query:
            return HTTPStatus.UNPROCESSABLE_ENTITY, ""
        try:
            n = int(query["n"][0])
        except (ValueError, IndexError):
            return HTTPStatus.UNPROCESSABLE_ENTITY, ""
        if n < 0:
            return HTTPStatus.BAD_REQUEST, ""
        fac = 1
        while n > 0:
            fac *= n
            n -= 1
        return HTTPStatus.OK, dumps({"result": fac})

    async def mean(
        self, path: Match, query: dict[str, Any], payload: str
    ) -> tuple[HTTPStatus, str]:
        try:
            numbers = loads(payload)
        except ValueError:
            return HTTPStatus.UNPROCESSABLE_ENTITY, ""
        if numbers is None:
            return HTTPStatus.UNPROCESSABLE_ENTITY, ""
        if not isinstance(numbers, list) or not numbers:
            return HTTPStatus.BAD_REQUEST, ""
        return HTTPStatus.OK, dumps({"result": sum(numbers) / len(numbers)})


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
    handler = Handler()
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                ...  # Do some startup here!
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                ...  # Do some shutdown here!
                await send({"type": "lifespan.shutdown.complete"})
                return
    elif scope["type"] == "http":
        await handler(scope, receive, send)
    else:
        raise NotImplementedError()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
