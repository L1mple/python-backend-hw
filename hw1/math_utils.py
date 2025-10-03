from typing import List

def calculate_factorial(n: int) -> int:
    """Вычисляет факториал неотрицательного целого числа n."""
    if n == 0:
        return 1
    result = 1
    for i in range(2, n + 1):
        result *= i
    return result

def calculate_fibonacci(n: int) -> int:
    """Вычисляет n-е число Фибоначчи (с 0-го индекса)."""
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

def calculate_mean(numbers: List[float]) -> float:
    """Вычисляет среднее арифметическое списка чисел."""
    if not numbers:
        raise ValueError("Array must not be empty.")
    return sum(numbers) / len(numbers)
