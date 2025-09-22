import math
import json
from http import HTTPStatus
from urllib import parse
from typing import Any, Awaitable, Callable


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
    if scope["type"] != "http":
        await send_response(
            send=send,
            status=HTTPStatus.INTERNAL_SERVER_ERROR,
            data={"error": "UnsupportedType", "message": "This application only supports HTTP"},
        )
        return

    method = scope["method"]
    path = scope["path"]

    if method != "GET":
        await send_response(
            send=send,
            status=HTTPStatus.NOT_FOUND,
            data={"error": "NotFound", "message": f"Path {path} not found for method {method}"},
        )
        return

    if path == "/factorial":
        query_params = parse.parse_qs(scope["query_string"].decode())
        n_str = query_params.get("n", [None])[0]

        if n_str is None or n_str == "":
            await send_response(
                send=send,
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                data={"error": "InvalidParameter", "message": "Query parameter 'n' is required"},
            )
            return
        try:
            n = int(n_str)
        except (ValueError, TypeError):
            await send_response(
                send=send,
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                data={"error": "InvalidParameter", "message": "'n' must be a valid integer"},
            )
            return

        if n < 0:
            await send_response(
                send=send,
                status=HTTPStatus.BAD_REQUEST,
                data={"error": "InvalidValue", "message": "'n' must be non-negative"},
            )
            return

        value = math.factorial(n)
        await send_response(send=send, status=HTTPStatus.OK, data={"result": value})
        return

    elif path.startswith("/fibonacci/"):
        path_parts = path.strip("/").split("/")

        if len(path_parts) != 2:
            await send_response(
                send=send, status=HTTPStatus.NOT_FOUND, data={"error": "NotFound", "message": "Invalid path format"}
            )
            return

        try:
            n = int(path_parts[1])
        except ValueError:
            await send_response(
                send=send,
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                data={"error": "InvalidParameter", "message": "Path parameter must be an integer"},
            )
            return

        if n < 0:
            await send_response(
                send=send,
                status=HTTPStatus.BAD_REQUEST,
                data={"error": "InvalidValue", "message": "'n' must be non-negative"},
            )
            return

        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b

        await send_response(send=send, status=HTTPStatus.OK, data={"result": a})
        return

    elif path == "/mean":
        event = await receive()
        body = event.get("body", b"")
        if not body:
            await send_response(
                send=send,
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                data={"error": "InvalidParameter", "message": "Request body cannot be empty"},
            )
            return

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            await send_response(
                send,
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "InvalidJSON", "message": "Could not decode request body"},
            )
            return

        if not isinstance(data, list):
            await send_response(
                send,
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": "InvalidFormat", "message": "Request body must be a JSON array"},
            )
            return

        if not data:
            await send_response(
                send,
                HTTPStatus.BAD_REQUEST,
                {"error": "InvalidValue", "message": "Input array cannot be empty"},
            )
            return

        if not all(isinstance(x, (int, float)) for x in data):
            await send_response(
                send=send,
                status=HTTPStatus.UNPROCESSABLE_ENTITY,
                data={"error": "InvalidParameter", "message": "All elements in the array must be numbers"},
            )
            return

        value = sum(data) / len(data)
        await send_response(send=send, status=HTTPStatus.OK, data={"result": value})
        return

    await send_response(
        send=send,
        status=HTTPStatus.NOT_FOUND,
        data={"error": "NotFound", "message": f"Path {path} not found"},
    )
    return


async def send_response(send, status: HTTPStatus, data: dict):
    body = json.dumps(data).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status.value,
            "headers": [(b"content-type", b"application/json; charset=utf-8")],
        }
    )
    await send({"type": "http.response.body", "body": body})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
