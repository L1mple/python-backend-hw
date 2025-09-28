from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs
from math import factorial
import json


def fibonacci(n: int):
    if n == 0:
        return 0
    elif n == 1:
        return 1
    
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


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

    if scope.get("path") and "/fibonacci" in scope.get("path"):
        val = scope.get("path")
        if val:
            param = val.replace("/fibonacci/", "")
            try: 
                param_int = int(param)
                res = fibonacci(param_int)

                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [[b'content-type', b'application/json']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': json.dumps({"result": res}).encode('utf-8'),
                })

            except:
                await send({
                    'type': 'http.response.start',
                    'status': 422,
                    'headers': [[b'content-type', b'application/json']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': json.dumps({"error": "Invalid parameter"}).encode('utf-8'),
                })

    elif scope.get("path") and "/factorial" in scope.get("path"):
        try:
            query = scope.get("query_string")
            query_str = query.decode('utf-8')
            params = parse_qs(query_str)
            n_values = params.get('n')

            if n_values:
                n = int(n_values[0])
                res = factorial(n)

                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [[b'content-type', b'application/json']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': json.dumps({"result": res}).encode('utf-8'),
                })
            else:
                await send({
                    'type': 'http.response.start',
                    'status': 422,
                    'headers': [[b'content-type', b'application/json']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': json.dumps({"error": "Not found n in params"}).encode('utf-8'),
                })

            
        except:
            await send({
                'type': 'http.response.start',
                'status': 422,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': json.dumps({"error": "Invalid parameter"}).encode('utf-8'),
            })



    elif scope.get("path") and "/mean" in scope.get("path"):
        try:
            query = scope.get("query_string")
            query_str = query.decode('utf-8')
            params = parse_qs(query_str)
            numbers_values = params.get('numbers')[0].split(",")
            
            int_numbs = []
            for n in numbers_values:
                int_numbs.append(int(n))
                
            average = sum(int_numbs) / len(int_numbs)

            if scope['type'] == 'http':
                await send({
                    'type': 'http.response.start',
                    'status': 200,
                    'headers': [[b'content-type', b'application/json']],
                })
                await send({
                    'type': 'http.response.body',
                    'body': json.dumps({"result": average}).encode('utf-8'),
                })
        except:
            await send({
                'type': 'http.response.start',
                'status': 422,
                'headers': [[b'content-type', b'application/json']],
            })
            await send({
                'type': 'http.response.body',
                'body': json.dumps({"error": "Invalid parameter"}).encode('utf-8'),
            })
            
    else:
        await send({
            'type': 'http.response.start',
            'status': 404,
            'headers': [[b'content-type', b'application/json']],
        })
        await send({
            'type': 'http.response.body',
            'body': json.dumps({"error": "Not found"}).encode('utf-8'),
        })

    

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8001, reload=True)
