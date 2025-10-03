import json
from typing import Any, Awaitable, Callable, List


async def send_json_response(
    send : Callable[[dict[str,Any]],Awaitable[None]], # корутина
    status_code : int,                                # статус ответа 
    data : dict,                                      # тело ответа
):
    content = json.dumps(data).encode("utf-8")

    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers" : [
                [b"Content-Type",b"application/json"],
                [b"Content-Length",str(len(content)).encode("utf-8")],
            ]
        }
    )

    await send({
        "type" : "http.response.body",
        "body" : content
    })

async def read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    return body

def calc_fib(n: int) -> int:
    if n<0:
        raise ValueError("num must be ge 0")
    a,b = 0,1
    while n>0:
        a,b = b, a+b 
        n-=1
    return a

def calc_fact(n: int) -> int:
    if n<0:
        raise ValueError("num must be ge 0")
    if n == 0:
        return 1
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

def calc_mean(numbers: List[float]) -> float:
    if not numbers:
        raise ValueError("there is no numbers")
    return sum(numbers) / len(numbers)
    

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

    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif message["type"] == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                break
        return

    if scope["type"] != "http":
        return 
    
    path =  scope["path"]
    query_string = scope["query_string"].decode("utf-8")

    if path.startswith("/fibonacci/"):
        try:
            n_str = path.split("/")[-1]
            n = int(n_str)
        except (ValueError, IndexError):
            await send_json_response(send, 422, {"error": "invalid list"})
            return

        try:
            result = calc_fib(n)
            await send_json_response(send, 200, {"result": result})
        except ValueError as e:
            await send_json_response(send, 400, {"error": str(e)})

    elif path == "/factorial":
        query_string = scope["query_string"].decode("utf-8")
        params = {}
        if query_string:
            for pair in query_string.split('&'):
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    params[key] = value

        if not params.get("n"):
            await send_json_response(send, 422, {"error": "no param n"})
            return

        try:
            n = int(params["n"])
        except ValueError:
            await send_json_response(send, 422, {"error": "invalid arg"})
            return

        try:
            result = calc_fact(n)
            await send_json_response(send, 200, {"result": result})
        except ValueError as e:
            await send_json_response(send, 400, {"error": str(e)})



    elif path == "/mean":
        body = await read_body(receive)
        if not body:
            await send_json_response(send, 422, {"error": "invalid list"})
            return

        try:
            numbers = json.loads(body)
            if not isinstance(numbers, list):
                raise TypeError
        except (json.JSONDecodeError, TypeError):
            await send_json_response(send, 422, {"error": "invalid arg"})
            return

        try:
            result = calc_mean([float(num) for num in numbers])
            await send_json_response(send, 200, {"result": result})
        except (ValueError, TypeError) as e:
            await send_json_response(send, 400, {"error": str(e) or "invalid arg"})
            
    else:
        await send_json_response(send, 404, {"error": "invalid endpoint"})

 
            

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)