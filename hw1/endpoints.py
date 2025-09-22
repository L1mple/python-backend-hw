from http import HTTPStatus
import json
from utils import Receive, Scope, Send, calculate_fibonacci, calculate_factorial, calculate_mean


async def fibonacci_endpoint(scope: Scope, receive: Receive, send: Send, value: str):
    if value.startswith('-') and value[1:].isdigit():
        await send_error_response(send, status=HTTPStatus.BAD_REQUEST)
    elif value.isdigit():
        response = str(calculate_fibonacci(int(value)))
        await send_ok_response(send, response.encode())
    else:
        await send_error_response(send, status=HTTPStatus.UNPROCESSABLE_ENTITY)


async def factorial_endpoint(scope: Scope, receive: Receive, send: Send, value: list):
    if len(value) and value[0].startswith('-') and value[0][1:].isdigit():
        await send_error_response(send, status=HTTPStatus.BAD_REQUEST)
    elif len(value) and value[0].isdigit():
        response = str(calculate_factorial(int(value[0])))
        await send_ok_response(send, response.encode())
    else:
        await send_error_response(send, status=HTTPStatus.UNPROCESSABLE_ENTITY)


async def mean_endpoint(scope: Scope, receive: Receive, send: Send, value: str):
    try:
        parsed = json.loads(value)
    except (json.JSONDecodeError, TypeError):
        await send_error_response(send, status=HTTPStatus.UNPROCESSABLE_ENTITY)

    if not all(isinstance(x, (int, float)) for x in parsed):
        await send_error_response(send, status=HTTPStatus.BAD_REQUEST)

    response = str(calculate_mean(parsed))
    await send_ok_response(send, response.encode())


async def send_ok_response(send: Send, response: bytes):
    await send_message(send=send, status=HTTPStatus.OK, body=response)


async def send_error_response(send: Send, status=HTTPStatus.NOT_FOUND):
    await send_message(send=send, status=status, body=b"")


async def send_message(send: Send, status: HTTPStatus, body: bytes):
    response_message = {
        "type": "http.response.start",
        "status": status,
    }
    print("Sending response start:", response_message)
    await send(response_message)

    response_message = {
        "type": "http.response.body",
        "body": body,
        "more_body": False,
    }
    print("Sending response body:", response_message)
    await send(response_message)