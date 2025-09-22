from http import HTTPStatus
import re
from urllib.parse import parse_qs

from endpoints import send_error_response, factorial_endpoint, fibonacci_endpoint, mean_endpoint
from utils import Receive, Scope, Send


async def application(
    scope: Scope,
    receive: Receive,
    send: Send,
):
    """
    Args:
        scope: Словарь с информацией о запросе
        receive: Корутина для получения сообщений от клиента
        send: Корутина для отправки сообщений клиенту
    """
    print(f"Beginning connection. Scope: ", scope)

    if scope["type"] == "lifespan":
        await handle_lifetime(scope, receive, send)
    elif scope["type"] == "http":
        await handle_http(scope, receive, send)

    print(f"Ending connection")


async def handle_lifetime(scope: Scope, receive: Receive, send: Send):
    assert scope["type"] == "lifespan"

    while True:
        message = await receive()
        print(f"Got message:", message)

        if message["type"] == "lifespan.startup":
            await send({"type": "lifespan.startup.complete"})
        elif message["type"] == "lifespan.shutdown":
            await send({"type": "lifespan.shutdown.complete"})
            break


async def handle_http(scope: Scope, receive: Receive, send: Send):
    assert scope["type"] == "http"

    if scope["method"] != "GET":
        await send_error_response(send, status=HTTPStatus.NOT_FOUND)
    elif (m := re.match("/fibonacci/([^/\s]*)", scope["path"])):
        await fibonacci_endpoint(scope, receive, send, value=m.group(1))
    elif scope["path"] == "/factorial":
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string).get("n", [])
        await factorial_endpoint(scope, receive, send, value=query_params)
    elif scope["path"] == "/mean":
        body = await read_body(receive)
        await mean_endpoint(scope, receive, send, value=body)
    else:
        await send_error_response(send, status=HTTPStatus.NOT_FOUND)


async def read_body(receive: Receive) -> str:
    body = b""
    more_body = True
    
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)
    
    return body.decode("utf-8")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
