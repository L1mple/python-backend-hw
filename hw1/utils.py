def fibonacci(n):
    n = int(n)
    if n <= 0:
        return []
    seq = [0, 1]
    for _ in range(2, n):
        seq.append(seq[-1] + seq[-2])
    return seq[:n]

def factorial(n):
    n = int(n)
    result = 1
    for i in range(2, n+1):
        result *= i
    return result

def mean(numbers):
    numbers = [float(x) for x in numbers.split(",")]
    return sum(numbers) / len(numbers)