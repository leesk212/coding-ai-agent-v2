"""Fibonacci sequence implementation with type hints."""

from typing import Union


def fibonacci(n: Union[int, float]) -> int:
    """Calculate the nth Fibonacci number.

    The Fibonacci sequence is a series where each number is the sum of the two
    preceding ones, starting from 0 and 1:
    F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2) for n > 1

    Args:
        n: The position in the Fibonacci sequence. Must be a non-negative integer.

    Returns:
        The nth Fibonacci number as an integer.

    Raises:
        TypeError: If n is not an integer or cannot be converted to one.
        ValueError: If n is negative.

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
        ValueError: n must be non-negative
    """
    # Handle float input that represents a whole number
    if isinstance(n, float):
        if not n.is_integer():
            raise TypeError(f"n must be an integer, got {type(n).__name__}")
        n = int(n)

    # Type validation
    if not isinstance(n, int):
        raise TypeError(f"n must be an integer, got {type(n).__name__}")

    # Edge case: negative numbers
    if n < 0:
        raise ValueError("n must be non-negative")

    # Base cases
    if n == 0:
        return 0
    if n == 1:
        return 1

    # Iterative calculation (efficient O(n) time, O(1) space)
    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr

    return curr


if __name__ == "__main__":
    # Example usage demonstrating various cases
    print("Fibonacci Sequence Examples:")
    print("-" * 40)

    # Test edge cases
    print(f"fibonacci(0) = {fibonacci(0)}")  # Base case: 0
    print(f"fibonacci(1) = {fibonacci(1)}")  # Base case: 1

    # Test normal cases
    print(f"fibonacci(5) = {fibonacci(5)}")
    print(f"fibonacci(10) = {fibonacci(10)}")
    print(f"fibonacci(20) = {fibonacci(20)}")

    # Test with float input (whole number)
    print(f"fibonacci(15.0) = {fibonacci(15.0)}")

    # Generate sequence
    print("\nFirst 15 Fibonacci numbers:")
    sequence = [fibonacci(i) for i in range(15)]
    print(sequence)

    # Demonstrate error handling
    print("\nError handling examples:")
    try:
        fibonacci(-3)
    except ValueError as e:
        print(f"fibonacci(-3) raises: {type(e).__name__}: {e}")

    try:
        fibonacci(3.5)
    except TypeError as e:
        print(f"fibonacci(3.5) raises: {type(e).__name__}: {e}")
