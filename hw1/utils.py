from typing import Any, Callable
import json

async def json_response(send: Callable, status: int, data: Any):
    """
    Формирует и отправляет HTTP-ответ с JSON-телом.
    
    Args:
        send: Корутина для отправки сообщений клиенту.
        status: HTTP-статус код.
        data: Данные для сериализации в JSON.
    """
    body = json.dumps(data).encode('utf-8')
    headers = [(b'content-type', b'application/json')]

    await send({"type": "http.response.start", "status": status, "headers": headers})
    await send({"type": "http.response.body", "body": body})

async def error_response(send: Callable, status: int, detail: str):
    """
    Формирует и отправляет ответ с ошибкой в JSON формате.
    
    Args:
        send: Корутина для отправки сообщений клиенту.
        status: HTTP-статус код ошибки.
        detail: Сообщение об ошибке.
    """
    error_message = {"detail": detail}
    await json_response(send, status, error_message)

async def get_request_body(receive: Callable) -> bytes:
    """Хелпер для чтения всего тела HTTP-запроса."""
    raw_body = b""
    while True:
        message = await receive()
        if message['type'] == 'http.request':
            raw_body += message.get('body', b'')
            if not message.get('more_body', False):
                break
        # Дополнительная обработка на случай пустых или неожиданных сообщений
        elif message['type'] != 'http.request' and not raw_body:
            break
    return raw_body
