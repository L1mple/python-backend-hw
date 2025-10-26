from http import HTTPStatus
from typing import Any, Optional, Union

from utils.utils import is_digit


def validate_number(
        n: str
) -> Optional[tuple[int, str]]:
    if not n or not is_digit(n):
        return HTTPStatus.UNPROCESSABLE_ENTITY.value, HTTPStatus.UNPROCESSABLE_ENTITY.phrase
    
    n = int(n)
    
    if n < 0:
        return HTTPStatus.BAD_REQUEST.value, HTTPStatus.BAD_REQUEST.phrase
    

def validate_list(
        l: Any
) -> Optional[tuple[int, str]]:
    if isinstance(l, list) and l == []:
        return HTTPStatus.BAD_REQUEST.value, HTTPStatus.BAD_REQUEST.phrase
    
    if not l:
        return HTTPStatus.UNPROCESSABLE_ENTITY.value, HTTPStatus.UNPROCESSABLE_ENTITY.phrase


def factorial(
        n: str
) -> int:
    n = int(n)

    factorial = 1
    for i in range(1, n + 1):
        factorial *= i

    return factorial


def fibonacci(
        n: str
) -> int:
    n = int(n)

    if n <= 1:
        return n
    else:
        return fibonacci(n - 1) + fibonacci(n - 2)


def mean(
        nums: list[Union[int, float]]
) -> Union[int, float]:
    return sum(nums)/len(nums)
