from http import HTTPStatus
import json
from utils.utils import (
    check_request_valid, 
    create_message, 
    create_start_message
)
from utils.math_functions import (
    factorial, 
    fibonacci, 
    mean, 
    validate_list, 
    validate_number
)
from typing import Any, Awaitable, Callable

import urllib


async def read_body(
        receive: Callable[[], Awaitable[dict[str, Any]]]
) -> str:
    body = b""
    while True:
        message = await receive()
        body += message.get("body", b"")
        if not message.get("more_body", False):
            break
    return body


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

    if scope['type'] == 'http':
        method = scope["method"]
        path = scope["path"]

        if not check_request_valid(method, path):
            status_code = HTTPStatus.NOT_FOUND.value
            body = {
                "result": HTTPStatus.NOT_FOUND.phrase
            }
        
        input_body = await read_body(receive)

        if path == "/factorial":
            query_string = scope["query_string"]
            parsed_query = urllib.parse.parse_qs(query_string.decode("utf-8"))
            if parsed_query.get("n"):
                n = parsed_query["n"][0]
            else:
                n = None

            validation_result = validate_number(n)
            if validation_result:
                status_code, data = validation_result
            else:
                data = factorial(n)
                status_code = HTTPStatus.OK.value

            body = {
                "result": data
            }
        
        elif "/fibonacci" in path:
            n = path.split("/")[-1]

            validation_result = validate_number(n)
            if validation_result:
                status_code, data = validation_result
            else:
                data = fibonacci(n)
                status_code = HTTPStatus.OK.value

            body = {
                "result": data
            }
        
        elif path == "/mean":
            input_body = input_body.decode()
            try:
                json_data = json.loads(input_body)
            except json.decoder.JSONDecodeError:
                json_data = []
                
            validation_result = validate_list(json_data)

            if validation_result:
                status_code, data = validation_result
            else:
                data = mean(json_data)
                status_code = HTTPStatus.OK.value
            
            body = {
                "result": data
            }
            
        await send(
            create_start_message(
                status_code=status_code
            )
        )

        await send(
            create_message(
                body=body
            )
        )

    elif scope["type"] == "lifespan":
        while True:
            message = await receive()
            t = message.get("type")
            if t == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            elif t == "lifespan.shutdown":
                await send({"type": "lifespan.shutdown.complete"})
                return


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
