from http import HTTPStatus
import json


def factorial(n: int) -> int:
    if n == 1:
        return 1
    if n == 0:
        return 1
    return n * factorial(n-1)

def fibonacci(n: int) -> int:
    if n == 0:
        return 0
    if n == 1:
        return 1
    return n + fibonacci(n-1)
    
def mean(numbers: list):
    return sum(numbers) / len(numbers)

def process_factorial(query_string) -> tuple[int, str]:
    code = HTTPStatus.OK
    body = ""
    if query_string.startswith(b"n="):
        _, n = query_string.decode().split("=")
        try:
            n = int(n)
            if n < 0:
                code = HTTPStatus.BAD_REQUEST
                body = json.dumps({"error": "Bad request"})
            else:
                body = json.dumps({"result": factorial(n)})
        except ValueError:
            code = HTTPStatus.UNPROCESSABLE_ENTITY
            body = json.dumps({"error": "Invalid number"})
    else:
        code = HTTPStatus.UNPROCESSABLE_ENTITY
        body = json.dumps({"error": "Missing query param n"})
    return (code, body)

def process_fibonacci(path: str) -> tuple[int, str]:
    code = HTTPStatus.OK
    body = ""
    _, n = path.split("fibonacci/")
    try:
        n = int(n)
        if n < 0:
            code = HTTPStatus.BAD_REQUEST
            body = json.dumps({"error": "Invalid number"})
        else:
            body = json.dumps({"result": fibonacci(n)})
    except ValueError:
        code = HTTPStatus.UNPROCESSABLE_ENTITY
        body = json.dumps({"error": "Invalid number"})
    return (code, body)