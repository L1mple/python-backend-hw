from typing import Any, Awaitable, Callable
from http import HTTPStatus
import json

async def fibonacci_iterative(n):
    a, b = 0, 1  # Initialize the first two numbers
    fib_sequence = []
    while n > 0:
        fib_sequence.append(a)
        a, b = b, a + b  # Update to the next pair
        n -= 1
    return fib_sequence

async def factorial(n):
    fact = 1
    for num in range(2, n + 1):
        fact *= num
    return fact

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

    status = HTTPStatus.NOT_FOUND
    answer = '' 

    # Extract path from scope
    path = scope.get("path", "")
    query_string = scope.get("query_string", "")

    if path == '/mean':
        print(path)
        print(query_string)
        
        try:
            body = await receive()
            print(body)
            if body["type"] == "http.request":
                data = body["body"]
                decoded_data = data.decode("utf-8")
                try:
                    body_list = eval(decoded_data)
                except ValueError:
                    status = HTTPStatus.UNPROCESSABLE_ENTITY
                    answer = ''
                
                if not isinstance(body_list, list):
                    status = HTTPStatus.UNPROCESSABLE_ENTITY
                else:
                    if not body_list:
                        status = HTTPStatus.BAD_REQUEST
                    else:
                        status = HTTPStatus.OK
                        print(body_list)
                        answer = {"result": str(sum(body_list) / len(body_list))}
        except Exception as e:
            status = HTTPStatus.UNPROCESSABLE_ENTITY
            answer = str(e)
    elif path.startswith('/fibonacci/'):
        digit_raw = path.replace('/fibonacci/', '')
        digit_int = ''
        try:
            digit_int = int(digit_raw)
        except ValueError:
            status = HTTPStatus.UNPROCESSABLE_ENTITY
            answer = ''
        
        if isinstance(digit_int, int):
            if digit_int < 0:
                status = HTTPStatus.BAD_REQUEST
                answer = ''
            else:
                status = HTTPStatus.OK
                answer = {"result": str(fibonacci_iterative(digit_int))}
                answer = {"result": "100"}
        else:
            status = HTTPStatus.UNPROCESSABLE_ENTITY
            
    elif path == '/factorial':
        if b'n=' in query_string:
            query_encoded = query_string.decode('utf-8')
            digit_raw = query_encoded.replace('n=', '')
            digit_int = ''
            try:
                digit_int = int(digit_raw)
            except ValueError:
                status = HTTPStatus.UNPROCESSABLE_ENTITY
                answer = ''

            if isinstance(digit_int, int):
                if digit_int < 0:
                    status = HTTPStatus.BAD_REQUEST
                    answer = ''
                else:
                    status = HTTPStatus.OK
                    # answer = {"result": str(factorial(digit_int))}
                    fact = 1
                    for num in range(2, digit_int + 1):
                        fact *= num
                    answer = {"result": str(fact)}
        else:
            status = HTTPStatus.UNPROCESSABLE_ENTITY
            


    # Send HTTP response
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                [b"content-type", b"application/json"],
            ]
        }
    )
    print(answer)
    await send(
        {
            "type": "http.response.body",
            "body": json.dumps(answer).encode("utf-8")
        }
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:application", host="0.0.0.0", port=8000, reload=True)
