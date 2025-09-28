import math
from typing import Any, Awaitable, Callable
from http import HTTPStatus

def factorial(data):
    # 1. проверяем что dict не пустой
    if not data or "n" not in data:
        return HTTPStatus.UNPROCESSABLE_ENTITY, -1
    raw_value = data.get("n", "")
    if raw_value == "":
        return HTTPStatus.UNPROCESSABLE_ENTITY, -1
    try:
        if int(raw_value) < 0:
            return HTTPStatus.BAD_REQUEST, -1
        res = math.factorial(int(raw_value))
        return HTTPStatus.OK, res
    except ValueError:
        return HTTPStatus.UNPROCESSABLE_ENTITY, -1

def fibonacci(n):
    try:
        if int(n) < 0:
            return HTTPStatus.BAD_REQUEST, -1
        a, b = 0, 1
        for _ in range(int(n)):
            a,b = b, a + b
        return HTTPStatus.OK, b
    except ValueError:
        return HTTPStatus.UNPROCESSABLE_ENTITY, -1

def mean(data):
    print("data", data)
    # 1. проверяем что dict не пустой
    if not data or "numbers" not in data or data["numbers"] == 'null':
        return HTTPStatus.UNPROCESSABLE_ENTITY, -1

    # 3. парсим строку
    raw_value = data.get("numbers", "")
    items = raw_value.split(",") if raw_value else []

    if len(items) == 0:
        return HTTPStatus.BAD_REQUEST, -1

    # 4. приводим к float
    fl_data =  [float(x) for x in items if x]
    res = sum(fl_data) / len(fl_data)
    return HTTPStatus.OK, res

def routing(path, query_string, json_body):
    parts = path.split("/")  # ['', 'fibonacci', '10']
    entity = parts[1] if len(parts) > 1 else ""
    param = parts[2] if len(parts) > 2 else ""
    params: dict[str, str] = {}
    if query_string:
        for pair in query_string.split("&"):
            if not pair:
                continue
            if "=" in pair:
                k, v = pair.split("=", 1)
                params[k] = v
            else:
                params[pair] = ""
    print("all: ", entity, param, params)

    match entity:
        case "fibonacci":
            return fibonacci(param)
        case "factorial":
            return factorial(params)
        case "mean":
            return mean({ "numbers": json_body.replace("[", "").replace("]", "") })
        case _:
            return HTTPStatus.NOT_FOUND, -1

async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    print("scope------>", scope)
    if scope["type"] == "lifespan":
        # просто отвечаем "готово"
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return
    else:
        req_body = b""
        more = True
        while more:
            event = await receive()
            if event["type"] != "http.request":
                break
            req_body += event.get("body", b"")
            more = event.get("more_body", False)

        status_code, res = routing(scope["path"], scope["query_string"].decode("utf-8"), req_body.decode())

        if status_code != HTTPStatus.OK:
            await send({
                "type": "http.response.start",
                "status": status_code,
                "headers": [],
            })
            await send({
                "type": "http.response.body",
                "body": b"",
            })
            return

        res_body = ('{"result": %d}' % res).encode()

        await send({
            "type": "http.response.start",
            "status": HTTPStatus.OK,
            "headers": [
                (b"content-type", b"application/json; charset=utf-8"),
                (b"content-length", str(len(res_body)).encode()),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": res_body,
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=3000, reload=True)
