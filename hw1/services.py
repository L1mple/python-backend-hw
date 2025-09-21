from typing import List

def factorial(n: int) -> int:
    if n < 0:
        return 0
    
    if n == 0:
        return 1
    
    return n * factorial(n - 1)


def fibonacci(n: int) -> int:
    if n <= 0:
        return 0
    
    elif n == 1:
        return 1
    
    else:
        return fibonacci(n - 1) + fibonacci(n - 2) 


def mean(numbers: List[any]) -> float:
    return sum(numbers) / len(numbers)
