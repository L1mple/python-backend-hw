import json
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


def factorial(n: int) -> int:
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result


def fibonacci(n: int) -> int:
    if n < 0:
        raise ValueError("Fibonacci is not defined for negative numbers")
    if n == 0:
        return 0
    if n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


def mean(numbers: list) -> float:
    if not numbers:
        raise ValueError("Cannot calculate mean of empty list")
    return sum(numbers) / len(numbers)


async def send_response(send, status_code: int, body: dict = None):
    if body is None:
        body = {}
    
    body_bytes = json.dumps(body).encode('utf-8')
    
    await send({
        'type': 'http.response.start',
        'status': status_code,
        'headers': [
            [b'content-type', b'application/json'],
            [b'content-length', str(len(body_bytes)).encode()],
        ],
    })
    
    await send({
        'type': 'http.response.body',
        'body': body_bytes,
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
    if scope['type'] == 'lifespan':
        while True:
            message = await receive()
            if message['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif message['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                break
        return
    
    if scope['type'] != 'http':
        return
    
    method = scope['method']
    path = scope['path']
    query_string = scope.get('query_string', b'').decode('utf-8')
    
    # GET /factorial
    if method == 'GET' and path == '/factorial':
        try:
            query_params = parse_qs(query_string)
            if 'n' not in query_params:
                await send_response(send, 422)
                return
                
            n_values = query_params['n']
            if not n_values or not n_values[0]:
                await send_response(send, 422)
                return
                
            try:
                n = int(n_values[0])
            except (ValueError, TypeError):
                await send_response(send, 422)
                return
                
            if n < 0:
                await send_response(send, 400)
                return
                
            result = factorial(n)
            await send_response(send, 200, {"result": result})
            return
            
        except Exception:
            await send_response(send, 500)
            return
    
    # GET /fibonacci/{n}
    elif method == 'GET' and path.startswith('/fibonacci/'):
        try:
            n_str = path[len('/fibonacci/'):]
            if not n_str:
                await send_response(send, 422)
                return
                
            try:
                n = int(n_str)
            except (ValueError, TypeError):
                await send_response(send, 422)
                return
                
            if n < 0:
                await send_response(send, 400)
                return
                
            result = fibonacci(n)
            await send_response(send, 200, {"result": result})
            return
            
        except Exception:
            await send_response(send, 500)
            return
    
    # GET /mean
    elif method == 'GET' and path == '/mean':
        try:
            body = b''
            while True:
                message = await receive()
                if message['type'] == 'http.request':
                    body += message.get('body', b'')
                    if not message.get('more_body', False):
                        break
            
            if not body:
                await send_response(send, 422)
                return
                
            try:
                data = json.loads(body.decode('utf-8'))
            except (json.JSONDecodeError, UnicodeDecodeError):
                await send_response(send, 422)
                return
                
            if not isinstance(data, list):
                await send_response(send, 422)
                return
                
            if len(data) == 0:
                await send_response(send, 400)
                return
                
            for item in data:
                if not isinstance(item, (int, float)):
                    await send_response(send, 422)
                    return
                    
            result = mean(data)
            await send_response(send, 200, {"result": result})
            return
            
        except Exception:
            await send_response(send, 500)
            return
    
    await send_response(send, 404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
