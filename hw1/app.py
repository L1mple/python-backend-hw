from typing import Any, Awaitable, Callable
import json
import json

async def application(
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
    ):
    
    path = scope.get("path", "")
    method = scope.get("method", "GET")
    
    if path not in ["/", "/fibonacci", "/factorial", "/mean"] and not path.startswith("/fibonacci/"):
        await send({
            'type':'http.response.start',
            'status':404,
            'headers': [[b"content-type", b"application/json"]]
        })
        await send({
            "type": "http.response.body", 
            "body": json.dumps({"detail": "Not Found"}).encode('utf-8')
        })
        return

    if path.startswith("/fibonacci/"):
        try:
            n = int(path[11:])
            if n < 0:
                await send_error(send, 400, "Number must be non-negative")
                return
            result = fibonacci(n)
            await send_success(send, result)
        except ValueError:
            await send_error(send, 422, "Invalid number format")

    elif path == "/factorial":
        if method != "GET":
            await send_error(send, 405, "Method not allowed")
            return
            
        query_string = scope.get("query_string", b"").decode()
        n = get_query_param(query_string, "n")
        
        if not n:
            await send_error(send, 422, "Missing parameter 'n'")
            return
            
        try:
            num = int(n)
            if num < 0:
                await send_error(send, 400, "Number must be non-negative")
                return
            result = factorial(num)
            await send_success(send, result)
        except ValueError:
            await send_error(send, 422, "Parameter 'n' must be an integer")

    elif path == "/mean":
        if method != "GET":
            await send_error(send, 405, "Method not allowed")
            return
            
        body = await receive_body(receive)
        if not body:
            await send_error(send, 422, "Missing JSON body")
            return
            
        try:
            numbers = json.loads(body)
            if not isinstance(numbers, list):
                await send_error(send, 422, "Body must be a list")
                return
                
            if not numbers:
                await send_error(send, 400, "List cannot be empty")
                return
                
            if not all(isinstance(x, (int, float)) for x in numbers):
                await send_error(send, 422, "All elements must be numbers")
                return
                
            result = mean(numbers)
            await send_success(send, result)
        except json.JSONDecodeError:
            await send_error(send, 422, "Invalid JSON format")

    elif path == "/":
        await send_error(send, 404, "Not Found")


async def receive_body(receive):
    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    return body.decode('utf-8') if body else ""

async def send_success(send, result):
    await send({
        'type':'http.response.start',
        'status':200,
        'headers': [[b"content-type", b"application/json"]]
    })
    await send({
        "type": "http.response.body", 
        "body": json.dumps({"result": result}).encode('utf-8')
    })

async def send_error(send, status_code, message):
    await send({
        'type':'http.response.start',
        'status':status_code,
        'headers': [[b"content-type", b"application/json"]]
    })
    await send({
        "type": "http.response.body", 
        "body": json.dumps({"detail": message}).encode('utf-8')
    })

def get_query_param(query_string, param_name):
    params = query_string.split("&")
    for param in params:
        if "=" in param:
            key, value = param.split("=", 1)
            if key == param_name:
                return value
    return None

def fibonacci(n):
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b

def factorial(n):
    if n == 0:
        return 1
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result

def mean(numbers):
    return sum(numbers) / len(numbers)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)