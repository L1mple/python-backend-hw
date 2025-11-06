from typing import Any, Awaitable, Callable
import json
from http import HTTPStatus
from router import Router, HTTPError, HTTPResponse, build_error_response
from handlers import handle_factorial, handle_fibonacci, handle_mean

router = Router()

router.add_route('GET', '/factorial',  handle_factorial)
router.add_route('GET', '/fibonacci/{n}',  handle_fibonacci)
router.add_route('GET', '/mean',  handle_mean)

async def application(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    """
    ASGI приложение с использованием шаблонного метода для роутинга
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
                return

    elif scope["type"] == "http":
        await handle_http_request(scope, receive, send)


async def handle_http_request(
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[dict[str, Any]]],
        send: Callable[[dict[str, Any]], Awaitable[None]],
):
    """Обработка HTTP запросов"""
    path = scope["path"]
    method = scope["method"]
    query_string = scope.get("query_string", b"").decode()

    response = HTTPResponse(status=HTTPStatus.OK, body={ 'result': 'None'})
    try:
        body = await parse_request_body(scope, receive)

        handler, context = await router.route(method, path, query_string, body)

        response: HTTPResponse = await handler(context)

    except HTTPError as e:
        response = build_error_response(e.status, e.error, e.message)
    except Exception as e:
        response = build_error_response(HTTPStatus.INTERNAL_SERVER_ERROR, 'Internal Server Error', str(e))
    finally:
        await send_response(send, response)


async def send_response(send: Callable, response: HTTPResponse):
    """Отправка ответов"""
    response_body = json.dumps(response['body']).encode("utf-8")

    await send({
        'type': 'http.response.start',
        'status': response['status'],
        'headers': [
            (b'content-type', b'application/json'),
            (b'content-length', str(len(response_body)).encode())
        ],
    })

    await send({
        'type': 'http.response.body',
        'body': response_body,
    })

async def parse_request_body(scope: dict[str, Any], receive: Callable) -> Any:
    """Загрузка тела запроса"""
    headers = dict(scope.get("headers", []))
    content_length = headers.get(b"content-length")

    if content_length:
        try:
            content_length = int(content_length.decode())
        except (ValueError, AttributeError):
            content_length = 0
    else:
        content_length = 0

    if content_length <= 0:
        return None

    body = b""
    more_body = True
    while more_body:
        message = await receive()
        body += message.get("body", b"")
        more_body = message.get("more_body", False)

    if not body:
        return None

    try:
        return json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, "Unprocessable Entity", "Invalid JSON format")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)