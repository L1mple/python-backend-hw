from typing import Callable
import json
from urllib.parse import parse_qs

from utils import json_response, error_response, get_request_body
from math_utils import calculate_factorial, calculate_fibonacci, calculate_mean


async def handle_factorial(scope: dict, _: Callable, send: Callable):
    """Обработчик для GET /factorial?n=..."""
    query_string = scope.get('query_string', b'')
    query_params = parse_qs(query_string)
    n_values = query_params.get(b'n')

    if not n_values:
        return await error_response(send, 422, "Missing query parameter 'n'")

    n_str = n_values[0].decode('utf-8')
    try:
        n = int(n_str)
        if n < 0:
            return await error_response(send, 400, "n must be a non-negative integer")
        
        result = calculate_factorial(n)
        response_data = {"n": n, "result": result}
        await json_response(send, 200, response_data)
        
    except ValueError:
        return await error_response(send, 422, "n must be a valid integer")
    
async def handle_fibonacci(scope: dict, _: Callable, send: Callable):
    """
    Обработчик для GET /fibonacci/{n}.
    Ожидает, что path_parts[1] содержит число n.
    """
    path = scope['path']
    path_parts = path.strip("/").split('/')
    
    if len(path_parts) != 2 or not path_parts[1]:
        return await error_response(send, 422, "Missing or invalid path parameter for fibonacci")

    n_str = path_parts[1]
    try:
        n = int(n_str)
        if n < 0:
            return await error_response(send, 400, "n must be a non-negative integer")
        
        result = calculate_fibonacci(n)
        response_data = {"n": n, "result": result}
        await json_response(send, 200, response_data)
        
    except ValueError:
        return await error_response(send, 422, "Path parameter 'n' must be a valid integer")
    
async def handle_mean(_: dict, receive: Callable, send: Callable):
    """Обработчик для GET /mean (JSON Body)"""
    raw_body = await get_request_body(receive)

    try:
        data = json.loads(raw_body.decode('utf-8')) if raw_body else None

        if data is None:
            return await error_response(send, 422, "Body must contain valid JSON array.")
        
        if not isinstance(data, list):
            return await error_response(send, 422, "Body must be a JSON array of numbers.")
        
        if not data:
            return await error_response(send, 400, "Array must not be empty.")
        
        numbers = []
        for item in data:
            if isinstance(item, (int, float)):
                numbers.append(float(item))
            else:
                return await error_response(send, 422, f"Array contains non-numeric value: {item}")
        
        result = calculate_mean(numbers)
        response_data = {"numbers": numbers, "result": result}
        await json_response(send, 200, response_data)

    except json.JSONDecodeError:
        return await error_response(send, 422, "Invalid JSON format.")
    except ValueError as e:
        return await error_response(send, 422, f"Bad Request: {e}")
