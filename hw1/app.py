from typing import Any, Awaitable, Callable
import json
import math


def fibonacchi(n):
    if n < 0:
        raise Exception()
    prev, ans = 0, 1
    for _ in range(n):
        prev, ans = ans, ans + prev
    return ans


def factorial(n):
    if n < 0:
        raise Exception()
    return math.factorial(n)


def mean(arr):
    if len(arr) == 0:
        raise Exception()
    return sum(arr) / len(arr)


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
    if 'path' in scope and scope['method'] == 'GET':
        splitted_path = scope['path'].split('/')
    else:
        splitted_path = [None, None]
    body = {"result": None}
    status = 200
    function = None
    try:
        if splitted_path[1] == 'fibonacci':
            val = splitted_path[2]
            assert '.' not in val
            param = int(val)
            function = fibonacchi
        elif splitted_path[1] == 'factorial':
            key, val = scope['query_string'].decode('utf-8').split('=')
            assert key == 'n'
            assert '.' not in val
            param = int(val)
            function = factorial
        elif splitted_path[1] == 'mean':
            if scope['query_string'] != b'':
                key, val = scope['query_string'].decode('utf-8').split('=')
                assert key == 'numbers'
            else:
                val = await receive()
                val = val['body'].decode('utf-8')
                assert val[0] == '[' and val[-1] == ']'
                val = val[1:-1]
            param = []
            if val != '':
                for num in val.split(','):
                    param.append(float(num))
            function = mean
        else:
            status = 404
    except:
        status = 422
    if function is not None:
        try:
            body = {"result": function(param)}
        except:
            status = 400
    await send({'type': 'http.response.start',
                'status': status,
               'headers': [[b'content-type', b'application/json']]})
    await send({'type': 'http.response.body', 'body': json.dumps(body).encode('utf-8')})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
