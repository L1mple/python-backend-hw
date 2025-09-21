from typing import Any, Awaitable, Callable
from operations import mean_number, fibonacci, factorial

import asyncio
import ast
import json


async def handle_query(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    body: bytes | None,
    query_path: str | None,
    query_params: bytes | None
):

    if not query_path:
        op_type = ''
    else:
        op_type = query_path.split('/')[1]

    try:
        if op_type not in {'mean', 'fibonacci', 'factorial'}:
            raise ValueError("Unknown or wrong operation type")

        elif op_type == 'mean':
            if query_params:
                raise ValueError("No query params supported for this operation")
            if not body:
                raise ValueError("Parameters should be in the body")
            numbers = body.decode()
            if numbers == 'null':
                raise ValueError("Body should consist of the list only")
            numbers = ast.literal_eval(numbers)
            if not isinstance(numbers, list):
                raise ValueError("Body should consist of the list only")
            result = str(await asyncio.to_thread(mean_number, numbers))

        elif op_type == 'fibonacci':
            if query_params:
                raise ValueError("No query params supported for this operation")
            if body:
                raise ValueError("Body should be empty for this operation")

            n = query_path.split('/')[2]
            if not n.lstrip('-').isnumeric():
                raise ValueError("Parameter is not a number")
            n = int(n)
            result = str(await asyncio.to_thread(fibonacci, n))

        elif op_type == 'factorial':
            if not query_params:
                raise ValueError("Arguments should be in query params")
            if body:
                raise ValueError("Body should be empty for this operation")

            params = query_params.decode().split('=')
            if len(params) != 2:
                raise ValueError("Specify only one parameter")
            if params[0] != 'n':
                raise ValueError("Parameter name should be `n`")
            if params[1] == '':
                raise ValueError("Empty parameter value")
            if not params[1].lstrip('-').isnumeric():
                raise ValueError("Parameter is not a number")
            n = int(params[1])
            result = str(await asyncio.to_thread(factorial, n))

        status_code = 200
        body = json.dumps({"result": result})

    except ValueError as e:
        body = str(e)
        if body == "Unknown or wrong operation type":
            status_code = 404
        elif body in {"No query params supported for this operation",
                      "Arguments should be in query params",
                      "Parameters should be in body",
                      "Body should be empty for this operations",
                      "Body should consist of the list only",
                      "Specify only one parameter",
                      "Parameter name should be `n`",
                      "Empty parameter value", "Parameter is not a number"}:
            status_code = 422
        else:
            status_code = 400
    except ZeroDivisionError:
        body = "Empty list for mean calculation"
        status_code = 400
    except IndexError:
        body = "No number for Fibonacci calculation"
        status_code = 422
    except TypeError:
        body = "Operation can be performed only with numbers"
        status_code = 400

    finally:
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    [b"content-type", b"text/plain"],
                ],
            }
        )
        await send({"type": "http.response.body", "body": body.encode('utf-8')})


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
            body_dict = await receive()
            if body_dict['type'] == 'lifespan.startup':
                await send({'type': 'lifespan.startup.complete'})
            elif body_dict['type'] == 'lifespan.shutdown':
                await send({'type': 'lifespan.shutdown.complete'})
                return

    if scope['type'] == 'http':
        body_dict = await receive()
        body = body_dict['body']

        query_path = scope['path']
        query_params = scope['query_string']

        await handle_query(send, body, query_path, query_params)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
