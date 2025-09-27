from typing import Any, Awaitable, Callable
import json 
import math
from urllib.parse import parse_qs

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
    query_string = scope.get('query_string', b'').decode('utf-8')
    query_params = parse_qs(query_string)

    async def send_response(status_code, body):
        await send({
            'type':'http.response.start', 
            'status': status_code, 
            'headers': [
                [b'content-type', b'application/json'], 
            ],
        })
        await send({
            'type': 'http.response.body', 
            'body': json.dumps(body).encode('utf-8'),
        })
    async def receive_body():
        body = b''
        while True:
            message = await receive()
            if message['type'] == 'http.request':
                body += message.get('body', 'b')
                if not message.get('more_body', False):
                    break
        if body:
            try:
                return json.loads(body.decode('utf-8'))
            except json.JSONDecodeError:
                return None
        return None
    if method != 'GET':
        await send_response(404, {})
        return
    
    try:
        if path == '/factorial':
            if 'n' not in query_params or not query_params['n'][0]:
                await send_response(422, {})
                return
            
            try:
                n = int(query_params['n'][0])
                if n < 0:
                    await send_response(400, {})
                    return
                
                result = math.factorial(n)
                await send_response(200, {'result': result})
                return
            except ValueError:
              await send_response(422, {})
              return
        

    except Exception:
        await send_response(500, {})
        return
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
