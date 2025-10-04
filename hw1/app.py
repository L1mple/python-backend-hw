from typing import Any, Awaitable, Callable
import json
import re



def parse_query_string(qs):
    """
    Парсит query string в словарь списков: 'n=5&x=3' → {'n': ['5'], 'x': ['3']}
    """
    if not qs:
        return {}
    parsed = {}
    pairs = qs.split('&')
    for pair in pairs:
        if '=' in pair:
            key, value = pair.split('=', 1)
            key = unquote(key)
            value = unquote(value)
            if key in parsed:
                parsed[key].append(value)
            else:
                parsed[key] = [value]
    return parsed


def unquote(string):
    """
    Минимальная реализация URL-декодирования без urllib.
    Поддерживает %XX и замену '+' на пробел.
    """
    string = string.replace('+', ' ')
    res = ""
    i = 0
    while i < len(string):
        if string[i] == '%' and i + 2 < len(string):
            try:
                hex_val = string[i+1:i+3]
                byte_val = bytes.fromhex(hex_val)
                char = byte_val.decode('utf-8')
                res += char
                i += 3
                continue
            except Exception:
                pass
        res += string[i]
        i += 1
    return res


async def send_json(send, status, data):
    """
    Отправляет JSON-ответ. Гарантированно совместима с ASGI/h11.
    """
    body = json.dumps(data, ensure_ascii=False).encode('utf-8')
    headers = [
        (b'content-type', b'application/json'),
    ]
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': headers,
    })
    await send({
        'type': 'http.response.body',
        'body': body,
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
    # TODO: Ваша реализация здесь

    if scope["type"] != "http":
        await send({
            "type": "http.response.start",
            "status": 400,
            "headers": [(b'content-type', b'text/plain')]
        })

        await send({
            "type": "http.response.body",
            "body": b"Only HTTP supported"
        })
        return

    path = scope["path"]
    method = scope["method"]

    if method != "GET":
        await send_json(send, 404, {"error": "Only GET methods allowed"})
        return

    if path == "/factorial" and method == "GET":
        await handle_factorial(scope, receive, send)

    elif path.startswith("/fibonacci") and method == "GET":
        await handle_fibonacci(scope, receive, send)

    elif path == "/mean" and method == "GET":
        await handle_mean(scope, receive, send)

    else:
        await send_json(send, 404, {"error": "Not Found"})


async def handle_factorial(scope, recieve, send):
    query_string = scope["query_string"].decode("utf-8")
    params = parse_query_string(query_string)

    if "n" not in params or len(params["n"]) == 0:
        await send_json(send, 422, {"error": "Missing query parameter: n"})
        return

    n_str = params["n"][0]

    try:
        n = int(n_str)
    except ValueError:
        await send_json(send, 422, {"error": "n must be an integer"})
        return

    if n < 0:
        await send_json(send, 400, {"error": "n must be a non-negative integer"})
        return

    result = 1
    for i in range(1, n + 1):
        result *= i

    await send_json(send, 200, {"result": result})



async def handle_fibonacci(scope, recieve, send):

    path = scope["path"]
    match = re.match(r"/fibonacci/(-?\d+)", path)

    if not match:
        await send_json(send, 422, {"error": "Invalid path format. Expected /fibonacci/<integer>"})
        return

    try:
        n = int(match.group(1))
    except ValueError:
        await send_json(send, 422, {"error": "n must be an integer"})
        return

    if n < 0:
        await send_json(send, 400, {"error": "n must be a non-negative integer"})
        return

    if n == 0:
        fib = 0

    elif n == 1:
        fib = 1

    else:
        a, b = 0, 1
        for i in range(2, n + 1):
            a, b = b, a + b
        fib = b

    await send_json(send, 200, {"result": fib})




async def handle_mean(scope, recieve, send):
    body = b""
    more_body = True

    while more_body:
        message = await recieve()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    if not body:
        await send_json(send, 422, {"error": "No body received"})
        return

    try:
        data = json.loads(body)
        if not isinstance(data, list):
            raise ValueError("Expected JSON Array")

        numbers = [float(x) for x in data]

    except (json.JSONDecodeError, ValueError, TypeError, OverflowError):
        await send_json(send, 422, {"error": "All values must be numbers"})
        return

    if len(numbers) == 0:
        await send_json(send, 400, {"error": "No values received"})
        return

    mean_value = sum(numbers) / len(numbers)
    await send_json(send, 200, {"result": mean_value})




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)