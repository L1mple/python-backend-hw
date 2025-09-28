from typing import Any, Awaitable, Callable
import json

#_________Отправка HTTP ответа_________
async def send_response(send, status_code, data):
    await send({
        "type": "http.response.start",
        "status": status_code,
        "headers": [[b"content-type", b"application/json"]]
    })
    
    await send({
        "type": "http.response.body",
        "body": json.dumps(data).encode()
    })


#_________Вычисление n-го числа Фибоначчи_________
def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(n-1):
        a, b = b, a + b
    return b

#_________Вычисление n-го факториала________
def factorial(n):
    if n < 0:
        raise ValueError("n must be non-negative")
    result = 1
    for i in range(n):
        result *= i
    return result

#_________Вычисление среднего значения списка_________
def mean(json_data):
    if not isinstance(json_data, list):
        raise ValueError("json must be a list")
    if not all(isinstance(item, (int, float)) for item in json_data):
        raise ValueError("json must contain only numbers")
    return sum(json_data) / len(json_data)


#_________Обработка /fibonacci/{n}_________
async def handle_fibonacci(send, path):
    try:
        n_str = path.split("/fibonacci/")[1]
        n = int(n_str)
        
        if n < 0:
            await send_response(send, 400, {"error": "Bad Request"})
            return
        
        result = fibonacci(n)
        await send_response(send, 200, {"result": result})
        
    except ValueError:
        await send_response(send, 422, {"error": "Unprocessable Entity"})
    except Exception:
        await send_response(send, 422, {"error": "Unprocessable Entity"})


#_________Обработка /factorial?n={n}_________
async def handle_factorial(send, scope):
    try:
        query_string = scope.get("query_string", b"").decode()
        
        if not query_string:
            await send_response(send, 422, {"error": "Unprocessable Entity"})
            return
        
        if "=" in query_string:
            key, value = query_string.split("=", 1)
        else:
            await send_response(send, 422, {"error": "Unprocessable Entity"})

        if key != "n":
            await send_response(send, 422, {"error": "Unprocessable Entity"})
            return

        if not value:
            await send_response(send, 422, {"error": "Unprocessable Entity"})
            return
        
        n = int(value)
        
        if n < 0:
            await send_response(send, 400, {"error": "Bad Request"})
            return
        
        result = factorial(n)
        await send_response(send, 200, {"result": result})
        
    except ValueError:
        await send_response(send, 422, {"error": "Unprocessable Entity"})
    except Exception:
        await send_response(send, 422, {"error": "Unprocessable Entity"})


#_________Обработка /mean_________
async def handle_mean(send, receive):
    try:
        message = await receive()
        body = message.get("body", b"")
        
        if not body:
            await send_response(send, 422, {"error": "Unprocessable Entity"})
            return
        
        data = json.loads(body.decode())
        
        if not isinstance(data, list):
            await send_response(send, 422, {"error": "Unprocessable Entity"})
            return

        if len(data) == 0:
            await send_response(send, 400, {"error": "Bad Request"})
            return
        
        result = mean(data)
        await send_response(send, 200, {"result": result})
        
    except json.JSONDecodeError:
        await send_response(send, 422, {"error": "Unprocessable Entity"})
    except Exception:
        await send_response(send, 422, {"error": "Unprocessable Entity"})


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
                break
        return

    method = scope["method"]
    path = scope["path"]
    
    if path.startswith("/fibonacci/"):
        await handle_fibonacci(send, path)
    elif path.startswith("/factorial"):
        await handle_factorial(send, scope)
    elif path.startswith("/mean"):
        await handle_mean(send, receive)
    else:
        await send_response(send, 404, {"error": "Not Found"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
