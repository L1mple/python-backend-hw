from typing import Any, Awaitable, Callable
from functools import lru_cache

Scope = dict[str, Any]
Receive = Callable[[], Awaitable[dict[str, Any]]]
Send = Callable[[dict[str, Any]], Awaitable[None]]


def calculate_fibonacci(n: int) -> int:
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b


@lru_cache(maxsize=128)
def calculate_factorial(n: int) -> int:
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    if n == 0 or n == 1:
        return 1
    return n * calculate_factorial(n - 1)


def calculate_mean(lst: list):
    if not lst:
        raise ValueError("Cannot calculate mean of empty list")
    
    return sum(lst) / len(lst)