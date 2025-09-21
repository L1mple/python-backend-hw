from typing import Any, Awaitable, Callable
from services import factorial, fibonacci, mean
import json
import re


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
    if scope['type'] != 'http':
        return
    
    method = scope['method']
    path = scope['path']

    if method != 'GET':
        await send_response(send, 404, {'error': 'Not found'})
        return

    if path == '/mean':
        await handle_mean(scope, receive, send)
    elif path.startswith('/fibonacci/'):
        await handle_fibonacci(path, send)
    elif path.startswith('/factorial'):
        await handle_factorial(scope, send)
    else:
        await send_response(send, 404, {'error': 'Not found'})


async def handle_fibonacci(path: str, send: Callable):
    try:
        n_str = path.split('/fibonacci/')[-1]
        n = int(n_str)
        
        if n < 0:
            await send_response(send, 400, {'error': 'Parameter "n" must be non-negative'})
            return
        
        result = fibonacci(n)
        await send_response(send, 200, {'result': result})
    except (ValueError, IndexError):
        # Теперь будет возвращать 422 вместо 404
        await send_response(send, 422, {'error': 'Invalid parameter format'})
    except Exception as e:
        await send_response(send, 500, {'error': f'Internal server error: {str(e)}'})


async def handle_mean(scope: dict[str, Any], receive: Callable, send: Callable):

    body = await get_request_body(receive)
    
    try:
        if not body:
            await send_response(send, 422, {'error': 'No data provided'})
            return
        
        data = json.loads(body)
        if not isinstance(data, list):
            await send_response(send, 400, {'error': 'Expected list of numbers'})
            return
        
        if len(data) == 0:
            await send_response(send, 400, {'error': 'Empty list'})
            return
        
        numbers = [float(num) for num in data]
        result = mean(numbers)
        
        await send_response(send, 200, {'result': result})
    except (ValueError, TypeError):
        await send_response(send, 422, {'error': 'Invalid numbers format'})
    except Exception as e:
        await send_response(send, 500, {'error': f'Internal server error: {str(e)}'})


async def handle_factorial(scope: dict[str, Any], send: Callable):
    query_string = scope.get('query_string', b'').decode()
    params = parse_query_params(query_string)
    
    if 'n' not in params:
        await send_response(send, 422, {'error': 'Missing "n" parameter'})
        return
    
    try:
        n = int(params['n'])
        if n < 0:
            await send_response(send, 400, {'error': 'Parameter "n" must be non-negative'})
            return
        
        result = factorial(n)
        await send_response(send, 200, {'result': result})
    except ValueError:
        await send_response(send, 422, {'error': 'Parameter "n" must be an integer'})
    except Exception as e:
        await send_response(send, 500, {'error': f'Internal server error: {str(e)}'})


async def get_request_body(receive: Callable) -> str:
    body = b''
    more_body = True
    
    while more_body:
        message = await receive()
        body += message.get('body', b'')
        more_body = message.get('more_body', False)
    
    return body.decode('utf-8')


def parse_query_params(query_string: str) -> dict:
    params = {}
    if query_string:
        for param in query_string.split('&'):
            if '=' in param:
                key, value = param.split('=', 1)
                params[key] = value
    return params


async def send_response(send: Callable, status: int, data: dict):
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [[b'content-type', b'application/json']],
    })
    await send({
        'type': 'http.response.body',
        'body': json.dumps(data).encode('utf-8'),
    })


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)