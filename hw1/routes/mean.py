import json
from http import HTTPStatus
from typing import Any, Awaitable, Callable

from helpers import read_body, send_json


async def handle_mean(
    scope: dict[str, Any],
    receive: Callable[[], Awaitable[dict[str, Any]]],
    send: Callable[[dict[str, Any]], Awaitable[None]],
):
    body = await read_body(receive)
    
    if not body:
        return await send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Request body is required"})
    
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return await send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Invalid JSON"})
    
    if not isinstance(data, list):
        return await send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "Data must be a list"})
    
    if len(data) == 0:
        return await send_json(send, HTTPStatus.BAD_REQUEST, {"error": "List cannot be empty"})
    
    for item in data:
        if not isinstance(item, (int, float)):
            return await send_json(send, HTTPStatus.UNPROCESSABLE_ENTITY, {"error": "All elements must be numbers"})
    
    result = calculate_mean(data)
    return await send_json(send, HTTPStatus.OK, {"result": result})


def calculate_mean(numbers: list[int | float]) -> float:
    return sum(numbers) / len(numbers)
