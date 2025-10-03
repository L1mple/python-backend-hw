from structures import HTTPError, HTTPResponse
from http import HTTPStatus
import math

async def handle_factorial(context: dict) -> HTTPResponse:
    """Обработка факториала"""
    query_params = context['query_params']

    if 'n' not in query_params:
        raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, "Unprocessable Entity", "Parameter 'n' is required")

    try:
        n = int(query_params['n'])
    except ValueError:
        raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, "Unprocessable Entity", "Parameter 'n' must be an integer")

    if n < 0:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Bad Request", "Parameter 'n' must be non-negative")

    try:
        result = math.factorial(n)
        return {
            'status': HTTPStatus.OK,
            'body': {'result': result}
        }
    except OverflowError:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Bad Request", "Parameter 'n' is too large")


async def handle_fibonacci(context: dict) -> HTTPResponse:
    """Обработка чисел Фибоначчи"""
    path_params = context['path_params']

    try:
        n = int(path_params['n'])
    except (KeyError, ValueError):
        raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, "Unprocessable Entity", "Invalid number parameter")

    if n < 0:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Bad Request", "Number must be non-negative")

    if n in [0, 1]:
        result = n
    else:
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        result = b

    return {
        'status': HTTPStatus.OK,
        'body': {'result': result}
    }


async def handle_mean(context: dict) -> HTTPResponse:
    """Обработка среднего значения"""
    body_data = context['body']

    if body_data is None:
        raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, "Unprocessable Entity", "JSON body is required")

    if not isinstance(body_data, list):
        raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, "Unprocessable Entity", "Expected a list of numbers")

    if not body_data:
        raise HTTPError(HTTPStatus.BAD_REQUEST, "Bad Request", "At least one number is required")

    try:
        numbers = [float(num) for num in body_data]
    except (TypeError, ValueError):
        raise HTTPError(HTTPStatus.UNPROCESSABLE_ENTITY, "Unprocessable Entity", "All values must be valid numbers")

    mean = sum(numbers) / len(numbers)
    return {
        'status': HTTPStatus.OK,
        'body': {'result': mean}
    }
