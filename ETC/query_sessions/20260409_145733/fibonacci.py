"""Fibonacci number calculation module with input validation and type hints."""

from __future__ import annotations


class FibonacciError(Exception):
    """Base exception for Fibonacci-related errors."""

    pass


class InvalidInputError(FibonacciError):
    """Raised when the input to fibonacci function is invalid."""

    pass


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    The Fibonacci sequence is a series of numbers where each number is the sum
    of the two preceding ones, starting from 0 and 1:
    0, 1, 1, 2, 3, 5, 8, 13, 21, 34, ...

    Args:
        n: The position in the Fibonacci sequence (0-indexed). Must be a
            non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        InvalidInputError: If n is not an integer or is negative.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
        >>> fibonacci(-5)
        Traceback (most recent call last):
            ...
        InvalidInputError: Input must be a non-negative integer, got -5
    """
    if not isinstance(n, int):
        raise InvalidInputError(
            f"Input must be an integer, got {type(n).__name__}"
        )
    if n < 0:
        raise InvalidInputError(
            f"Input must be a non-negative integer, got {n}"
        )

    if n <= 1:
        return n

    prev: int = 0
    curr: int = 1

    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr

    return curr


if __name__ == "__main__":
    # Example usage demonstrating the fibonacci function
    print("Fibonacci Sequence Example")
    print("-" * 40)

    # Calculate and display first 15 Fibonacci numbers
    print("First 15 Fibonacci numbers:")
    for i in range(15):
        print(f"F({i}) = {fibonacci(i)}")

    print("-" * 40)

    # Demonstrate error handling
    print("\nError handling examples:")
    test_cases = [5, 10, 15, -1, 3.5, "ten"]

    for test_input in test_cases:
        try:
            result = fibonacci(test_input)
            print(f"fibonacci({test_input}) = {result}")
        except InvalidInputError as e:
            print(f"fibonacci({test_input}) raised InvalidInputError: {e}")
