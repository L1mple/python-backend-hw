from typing import Any, Awaitable, Callable
from http import HTTPStatus
import json

async def NotOK(send: Callable[[dict[str, Any]], Awaitable[None]], status: HTTPStatus, message: str):
    await send({
        'type': 'http.response.start',
        'status': status,
        'headers': [[b'content-type', b'text/plain']]
    })
    await send({'type': 'http.response.body', 'body': message.encode()})

def app(func):
    async def wrapper(arg, send):
        await send({
            'type': 'http.response.start',
            'status': HTTPStatus.OK,
            'headers': [
                [b'content-type', b'text/plain'],
            ],
        })
        await send({
            'type': 'http.response.body',
            'body': json.dumps({'result': func(arg)}).encode(),
        })
    return wrapper

@app
def fibonacci(n: int) -> int:
    def helper(n: int) -> int:
        if n < 0:
            raise ValueError("n must be non-negative")
        return n if n <= 1 else helper(n - 1) + helper(n - 2)
    return helper(n)

@app
def factorial(n: int) -> int:
    def helper(n: int) -> int:
        if n < 0:
            raise ValueError("n must be non-negative")
        return 1 if n == 0 else n * helper(n - 1)
    return helper(n)

@app
def mean(numbers: list[int]) -> float:
    if not numbers:
        raise ValueError("empty list")
    return sum(numbers) / len(numbers)
