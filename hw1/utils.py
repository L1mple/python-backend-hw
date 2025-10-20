from http import HTTPStatus
import json
from typing import Callable, Any, Awaitable


async def send_response(
    message: dict[str, Any], 
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: int = HTTPStatus.OK,
):
    await send({
        "type": "http.response.start",
        "status": status,
        "headers": [(b"Content-Type", b"text/plain")],
    }) 
    await send({
        "type": "http.response.body",
        "body": json.dumps(message).encode(),
    })

async def handle_404(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    await send({
        "type": "http.response.start",
        "status": HTTPStatus.NOT_FOUND,
        "headers": [(b"Content-Type", b"text/plain")],
    })
    await send({
        "type": "http.response.body",
        "body": b"Not Found",
    })