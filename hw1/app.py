import json
from typing import Any, Awaitable, Callable


def get_fibonacci_n(path: str) -> int:
    _, n = path.rsplit("/", 1)
    return int(n)


def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("n should be non-negative")
    if n < 2:
        return n
    a, b = 0, 1
    for _ in range(n - 2):
        a, b = a + b, a
    return b


def mean(numbers: list[int]) -> float:
    if not numbers:
        raise ValueError("Empty list")
    return sum(numbers) / len(numbers)


def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("n should be non-negative")
    res = 1
    mul = 1
    for _ in range(n):
        res *= mul
        mul += 1
    return res


def parse_query_params(query_params: bytes) -> dict[bytes, bytes]:
    if not query_params:
        return {}
    query_groups = [query_group.split(b"=") for query_group in query_params.split(b"&")]
    return {query_group[0]: query_group[1] for query_group in query_groups}


async def _send_response(send, message: str, status: int) -> None:
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"content-type", b"text/plain")],
    })
    await send({
        "type": "http.response.body",
        "body": message.encode(),
    })


async def _send_result(send, result) -> None:
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [(b"content-type", b"application/json")],
    })
    await send({
        "type": "http.response.body",
        "body": json.dumps({"result": result}).encode(),
    })


async def get_json_body(receive):
    res = []
    while True:
        message = await receive()
        res.append(message["body"])
        if not message.get("more_body", False):
            return json.loads(b"".join(res))


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

    send_response = lambda *args, **kwargs: _send_response(send, *args, **kwargs)
    send_result = lambda *args, **kwargs: _send_result(send, *args, **kwargs)
    path = scope["path"]
    method_name = path.split("/")[1]
    if method_name not in ("fibonacci", "mean", "factorial"):
        return await send_response("Wrong method", 404)
    elif method_name == "fibonacci":
        try:
            n = get_fibonacci_n(path)
        except ValueError:
            return await send_response("Could not parse n", 422)
        try:
            res = fibonacci(n)
        except ValueError:
            return await send_response("Could not calculate fibonacci", 400)
        return await send_result(res)
    query_params = parse_query_params(scope["query_string"])
    if method_name == "mean":
        numbers = await get_json_body(receive)
        if not numbers:
            if numbers is None:
                return await send_response("empty body", 422)
            if numbers is None:
                return await send_response("empty list", 400)
        try:
            res = mean(numbers)
        except ValueError:
            return await send_response("Empty list", 400)
        return await send_result(res)
    elif method_name == "factorial":
        if b"n" not in query_params:
            return await send_response("n required for factorial", 422)
        try:
            n = int(query_params[b"n"])
        except ValueError:
            return await send_response("Could not parse n", 422)
        try:
            res = factorial(n)
        except ValueError:
            return await send_response("Could not calculate factorial", 400)
        return await send_result(res)
    assert 0


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
