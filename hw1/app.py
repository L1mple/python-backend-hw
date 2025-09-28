import json
import math
from typing import Any, Awaitable, Callable
from urllib.parse import parse_qs


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
    
    # Parse request
    method = scope.get("method", "GET")
    path = scope.get("path", "/")
    query_string = scope.get("query_string", b"").decode("utf-8")
    
    # Helper function to send JSON response
    async def send_json_response(status_code: int, data: dict):
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps(data).encode("utf-8"),
        })
    
    # Helper function to send error response
    async def send_error_response(status_code: int, message: str = ""):
        await send({
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        })
        body = json.dumps({"error": message}) if message else b""
        await send({
            "type": "http.response.body",
            "body": body.encode("utf-8") if isinstance(body, str) else body,
        })
    
    # Helper function to read request body
    async def read_body():
        body = b""
        while True:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    break
        return body
    
    # Only handle GET requests
    if method != "GET":
        await send_error_response(404)
        return
    
    # Route handling
    if path.startswith("/fibonacci/"):
        # Extract n from path
        try:
            n_str = path[11:]  # Remove "/fibonacci/"
            if not n_str:
                await send_error_response(422, "Invalid path parameter")
                return
            
            n = int(n_str)
            if n < 0:
                await send_error_response(400, "Parameter n must be non-negative")
                return
            
            # Calculate fibonacci
            def fibonacci(num):
                if num <= 1:
                    return num
                a, b = 0, 1
                for _ in range(2, num + 1):
                    a, b = b, a + b
                return b
            
            result = fibonacci(n)
            await send_json_response(200, {"result": result})
            
        except ValueError:
            await send_error_response(422, "Invalid path parameter")
    
    elif path == "/factorial":
        # Parse query parameters
        query_params = parse_qs(query_string)
        
        if "n" not in query_params:
            await send_error_response(422, "Missing required parameter 'n'")
            return
        
        try:
            n_values = query_params["n"]
            if not n_values or not n_values[0]:
                await send_error_response(422, "Parameter 'n' cannot be empty")
                return
            
            n = int(n_values[0])
            if n < 0:
                await send_error_response(400, "Parameter n must be non-negative")
                return
            
            # Calculate factorial
            result = math.factorial(n)
            await send_json_response(200, {"result": result})
            
        except ValueError:
            await send_error_response(422, "Invalid parameter value")
    
    elif path == "/mean":
        # Read and parse JSON body
        try:
            body = await read_body()
            if not body:
                await send_error_response(422, "Missing request body")
                return
            
            numbers = json.loads(body.decode("utf-8"))
            
            if not isinstance(numbers, list):
                await send_error_response(422, "Request body must be a JSON array")
                return
            
            if len(numbers) == 0:
                await send_error_response(400, "Array cannot be empty")
                return
            
            # Validate all elements are numbers
            for num in numbers:
                if not isinstance(num, (int, float)):
                    await send_error_response(422, "All array elements must be numbers")
                    return
            
            # Calculate mean
            result = sum(numbers) / len(numbers)
            await send_json_response(200, {"result": result})
            
        except json.JSONDecodeError:
            await send_error_response(422, "Invalid JSON")
        except Exception:
            await send_error_response(422, "Invalid request")
    
    else:
        # 404 for any other path
        await send_error_response(404)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
