from typing import Any, Awaitable, Callable
from http import HTTPStatus

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

    method = scope["method"]
    path = scope["path"]
    
    # print("Path:", type(HTTPStatus.NOT_FOUND), file=sys.stderr)

    # Обрабатываем только существующие эндпоинты
    if len(path.split("/")) > 1:
        if path.split("/")[1] not in ["fibonacci", "factorial", "mean"]:
            await send_error(send, HTTPStatus.NOT_FOUND, "Not Found")
            return
    
    path_part0 = path.split("/")[1]

    if method != "GET":
        await send_error(send, HTTPStatus.NOT_FOUND, "Not Found")
        return

    try:
        if path_part0 == "fibonacci":
            await handle_fibonacci(scope, send)
        elif path_part0 == "factorial":
            await handle_factorial(scope, send)
        elif path_part0 == "mean":
            await handle_mean(scope, receive, send)
    
    except Exception:
        await send_error(send, 500, "Internal Server Error")


async def handle_fibonacci(scope: dict[str, Any], send: Callable):
    path = scope["path"]

    path_parts = path.split("/")
    if len(path_parts) != 3 or not path_parts[2]:
        await send_error(send, 422, "Unprocessable Entity")
        return

    try:
        n_str = path_parts[2]
        n = int(n_str)
    except ValueError:
        await send_error(send, 422, "Unprocessable Entity")
        return

    if n < 0:
        await send_error(send, 400, "Bad Request")
        return

    result = fibonacci(n)
    response_body = f'{{"result": {result}}}'.encode('utf-8')
    await send_response(send, 200, response_body)


async def handle_factorial(scope: dict[str, Any], send: Callable):
    query_string = scope.get("query_string", b"").decode()
    params = parse_query_string(query_string)
    
    if "n" not in params:
        await send_error(send, 422, "Unprocessable Entity")
        return

    n_str = params["n"]
    if not n_str:
        await send_error(send, 422, "Unprocessable Entity")
        return

    try:
        n = int(n_str)
    except ValueError:
        await send_error(send, 422, "Unprocessable Entity")
        return

    if n < 0:
        await send_error(send, 400, "Bad Request")
        return

    result = factorial(n)
    response_body = f'{{"result": {result}}}'.encode('utf-8')
    await send_response(send, 200, response_body)


async def handle_mean(scope: dict[str, Any], receive: Callable, send: Callable):
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    if not body:
        query_string = scope.get("query_string", b"").decode()
        params = parse_query_string(query_string)
        if "numbers" in params:
            numbers_str = params["numbers"]
            numbers_list = numbers_str.split(',')
            try:
                numbers = [float(x) for x in numbers_list]
                result = mean(numbers)
                response_body = f'{{"result": {result}}}'.encode('utf-8')
                await send_response(send, 200, response_body)
                return
            except ValueError:
                await send_error(send, 422, "Unprocessable Entity")
                return
    
    if not body:
        await send_error(send, 422, "Unprocessable Entity")
        return

    try:
        body_str = body.decode('utf-8').strip()

        if body_str == "null":
            await send_error(send, 422, "Unprocessable Entity")
            return

        if not body_str.startswith('[') or not body_str.endswith(']'):
            await send_error(send, 422, "Unprocessable Entity")
            return
            
        numbers_str = body_str[1:-1].strip()
        
        if not numbers_str:
            await send_error(send, 400, "Bad Request")
            return
            
        numbers_list = numbers_str.split(',')
        numbers = []
        
        for num_str in numbers_list:
            num_str = num_str.strip()
            try:
                num = float(num_str)
                numbers.append(num)
            except ValueError:
                await send_error(send, 422, "Unprocessable Entity")
                return
                
    except Exception:
        await send_error(send, 422, "Unprocessable Entity")
        return

    result = mean(numbers)
    response_body = f'{{"result": {result}}}'.encode('utf-8')
    await send_response(send, 200, response_body)


async def send_error(send: Callable, status: int, message: str):
    body = f'{{"error": "{message}"}}'.encode('utf-8')
    
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(body)).encode()]
        ],
    })
    await send({
        "type": "http.response.body", 
        "body": body
    })
    

async def send_response(send: Callable, status: int, body: bytes):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [
            [b"content-type", b"application/json"],
            [b"content-length", str(len(body)).encode()]
        ],
    })
    await send({
        "type": "http.response.body",
        "body": body
    })


def parse_query_string(query_string: str) -> dict:
    params = {}
    if query_string:
        for param in query_string.split("&"):
            if "=" in param:
                key, value = param.split("=", 1)
                params[key] = value
    return params


def fibonacci(n: int) -> int:
    if n == 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def factorial(n: int) -> int:
    if n == 0:
        return 1
    
    fac = 1
    for i in range(1, n + 1):
        fac = fac * i
    return fac


def mean(numbers: list[float]) -> float:
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
