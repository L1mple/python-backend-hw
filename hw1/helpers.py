import json
from http import HTTPStatus
from typing import Any, Awaitable, Callable

async def read_body(receive: Callable[[], Awaitable[dict[str, Any]]]) -> bytes:
    """
    Читает тело HTTP-запроса целиком, собирая все чанки http.request
    до тех пор, пока more_body == False.
    """
    body = bytearray()
    while True:
        event = await receive()
        assert event["type"] == "http.request"
        body.extend(event.get("body", b""))
        if not event.get("more_body", False):
            break

    return bytes(body)


async def send_json(
    send: Callable[[dict[str, Any]], Awaitable[None]],
    status: HTTPStatus | int,
    response: dict[str, Any] | str,
    headers: list[tuple[bytes, bytes]] | None = None,
) -> None:    
    hdrs: list[tuple[bytes, bytes]] = [
        (b"content-type", b"application/json"),
    ]
    if headers:
        hdrs.extend(headers)

    if isinstance(response, dict):
        body_content = json.dumps(response).encode("utf-8")
    else:
        body_content = str(response).encode("utf-8")

    await send(
        {
            "type": "http.response.start",
            "status": int(status),
            "headers": hdrs,
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body_content,
            "more_body": False,
        }
    )
