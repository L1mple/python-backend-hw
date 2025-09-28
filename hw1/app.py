import json
import math
from http import HTTPStatus
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
import re

async def handle_factorial(query_params: dict, **kwargs) -> tuple[int, dict]:
    try:
        n_str = query_params["n"][0]
        n = int(n_str)
    except (KeyError, IndexError, ValueError):
        return HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Параметр 'n' должен быть корректным целым числом"}

    if n < 0:
        return HTTPStatus.BAD_REQUEST, {"error": "Факториал не определен для отрицательных чисел"}

    try:
        result = math.factorial(n)
        return HTTPStatus.OK, {"result": result}
    except OverflowError:
        return HTTPStatus.BAD_REQUEST, {"error": "Результат слишком велик для вычисления"}

def get_fibonacci(n: int) -> int:
    if n == 0:
        return 0
    
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


async def handle_fibonacci(path_params: dict, **kwargs) -> tuple[int, dict]:
    n_str = path_params.get("n", "")

    try:
        n = int(n_str)
    except (ValueError, TypeError):
        return HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Параметр 'n' должен быть целым числом"}

    if n < 0:
        return HTTPStatus.BAD_REQUEST, {"error": "Числа Фибоначчи не определены для отрицательных чисел"}

    try:
        result = get_fibonacci(n)
        return HTTPStatus.OK, {"result": result}
    except OverflowError:
        return HTTPStatus.BAD_REQUEST, {"error": "Результат слишком велик для вычисления"}


async def handle_mean(json_body: dict | None, **kwargs) -> tuple[int, dict]:
    if not isinstance(json_body, list):
        return HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Тело запроса должно содержать JSON-список"}

    if not all(isinstance(value, (int, float)) for value in json_body):
        return HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Все значения в списке должны быть числами"}


    try:
        mean_value = sum(json_body) / len(json_body)
        return HTTPStatus.OK, {"result": mean_value}
    except ZeroDivisionError:
        return HTTPStatus.BAD_REQUEST, {"error": "Невозможно вычислить среднее значение для пустого списка"}



async def send_response(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int,
    body: dict[str, Any],
) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [[b"Content-Type", b"application/json"]],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": json.dumps(body).encode("utf-8"),
        }
    )


def create_router(routes: list[tuple[str, Callable]]) -> Callable:
    compiled_routes = []
    for path, handler in routes:
        path_regex = re.sub(r"{(\w+)}", r"(?P<\1>[^/]+)", path)
        compiled_routes.append((re.compile(f"^{path_regex}$"), handler))

    def resolve(path: str) -> tuple[Callable | None, dict]:
        for pattern, handler in compiled_routes:
            match = pattern.match(path)
            if match:
                return handler, match.groupdict()
        return None, {}

    return resolve

ROUTES = [
    ("/factorial", handle_factorial),
    ("/fibonacci/{n}", handle_fibonacci),
    ("/mean", handle_mean),
]

resolve_route = create_router(ROUTES)


async def handle_http_request(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
    if scope["method"] != "GET":
        await send_response(send, HTTPStatus.NOT_FOUND, {"error": f"Путь {scope['path']} не найден"})
        return

    handler, path_params = resolve_route(scope["path"])

    if not handler:
        await send_response(send, HTTPStatus.NOT_FOUND, {"error": f"Путь {scope['path']} не найден"})
        return

    body_bytes = b""
    more_body = True
    while more_body:
        message = await receive()
        body_bytes += message.get("body", b"")
        more_body = message.get("more_body", False)

    json_body = None
    if body_bytes:
        try:
            json_body = json.loads(body_bytes)
        except json.JSONDecodeError:
            await send_response(send, HTTPStatus.BAD_REQUEST, {"error": "Неверный JSON в теле запроса"})
            return

    query_string = scope.get("query_string", b"").decode("utf-8")
    query_params = parse_qs(query_string)

    status, body = await handler(
        query_params=query_params, path_params=path_params, json_body=json_body
    )
    await send_response(send, status, body)


async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
) -> None:
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
    elif scope["type"] == "http":
        await handle_http_request(scope, receive, send)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
