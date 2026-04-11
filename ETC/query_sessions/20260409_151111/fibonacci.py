"""
Fibonacci Number Calculator

This module provides multiple implementations of the Fibonacci sequence
calculator with proper type hints and comprehensive documentation.
"""

from functools import lru_cache
from typing import Dict


def fibonacci_iterative(n: int) -> int:
    """
    Calculate the nth Fibonacci number using an iterative approach.

    This method is efficient for large values of n and avoids recursion
    depth issues.

    Args:
        n: The position in the Fibonacci sequence (0-indexed).
           Must be a non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci_iterative(0)
        0
        >>> fibonacci_iterative(1)
        1
        >>> fibonacci_iterative(10)
        55
        >>> fibonacci_iterative(-5)
        Traceback (most recent call last):
            ...
        ValueError: n must be a non-negative integer
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")

    if n <= 1:
        return n

    prev: int = 0
    curr: int = 1

    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr

    return curr


def fibonacci_recursive(n: int) -> int:
    """
    Calculate the nth Fibonacci number using a recursive approach.

    This is a direct translation of the mathematical definition but
    has exponential time complexity O(2^n). Use only for small values
    of n or when educational purposes are the goal.

    Args:
        n: The position in the Fibonacci sequence (0-indexed).
           Must be a non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci_recursive(0)
        0
        >>> fibonacci_recursive(1)
        1
        >>> fibonacci_recursive(5)
        5
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")

    if n <= 1:
        return n

    return fibonacci_recursive(n - 1) + fibonacci_recursive(n - 2)


@lru_cache(maxsize=None)
def fibonacci_memoized(n: int) -> int:
    """
    Calculate the nth Fibonacci number using memoization.

    This recursive implementation uses Python's functools.lru_cache
    decorator to cache results and achieve O(n) time complexity.
    It's the recommended approach for most use cases.

    Args:
        n: The position in the Fibonacci sequence (0-indexed).
           Must be a non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci_memoized(0)
        0
        >>> fibonacci_memoized(1)
        1
        >>> fibonacci_memoized(10)
        55
        >>> fibonacci_memoized(50)
        12586269025
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")

    if n <= 1:
        return n

    return fibonacci_memoized(n - 1) + fibonacci_memoized(n - 2)


def fibonacci_with_cache(n: int, cache: Dict[int, int]) -> int:
    """
    Calculate the nth Fibonacci number using a custom cache dictionary.

    This implementation provides more control over the caching behavior
    and is useful when you need to manage the cache manually or share
    it across multiple calls.

    Args:
        n: The position in the Fibonacci sequence (0-indexed).
           Must be a non-negative integer.
        cache: A dictionary for memoization. Should be pre-populated
               with {0: 0, 1: 1} for best results.

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> cache = {0: 0, 1: 1}
        >>> fibonacci_with_cache(10, cache)
        55
        >>> cache  # doctest: +SKIP
        {0: 0, 1: 1, 2: 1, 3: 2, 4: 3, 5: 5, 6: 8, 7: 13, 8: 21, 9: 34, 10: 55}
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")

    if n in cache:
        return cache[n]

    # Ensure base cases are in cache
    if 0 not in cache:
        cache[0] = 0
    if 1 not in cache:
        cache[1] = 1

    cache[n] = fibonacci_with_cache(n - 1, cache) + fibonacci_with_cache(n - 2, cache)
    return cache[n]


def fibonacci(n: int) -> int:
    """
    Calculate the nth Fibonacci number (default implementation).

    This is the primary public API function that uses the memoized
    recursive approach for optimal performance.

    The Fibonacci sequence is defined as:
        F(0) = 0
        F(1) = 1
        F(n) = F(n-1) + F(n-2) for n > 1

    Args:
        n: The position in the Fibonacci sequence (0-indexed).
           Must be a non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(5)
        5
        >>> fibonacci(10)
        55
        >>> fibonacci(20)
        6765
    """
    return fibonacci_memoized(n)


if __name__ == "__main__":
    # Example usage and demonstration
    print("Fibonacci Sequence Calculator")
    print("-" * 40)

    # Test edge cases
    print("\nEdge Cases:")
    for value in [0, 1, -1]:
        try:
            result = fibonacci(value)
            print(f"fibonacci({value}) = {result}")
        except ValueError as e:
            print(f"fibonacci({value}) raised ValueError: {e}")

    # Calculate some Fibonacci numbers
    print("\nFirst 15 Fibonacci Numbers:")
    print("-" * 40)
    for i in range(15):
        print(f"F({i:2d}) = {fibonacci(i):15d}")

    # Compare implementations
    print("\nComparison of Implementations (n=20):")
    print("-" * 40)
    print(f"fibonacci_iterative(20) = {fibonacci_iterative(20)}")
    print(f"fibonacci_memoized(20)  = {fibonacci_memoized(20)}")
    print(f"fibonacci_with_cache(20) = {fibonacci_with_cache(20, {0: 0, 1: 1})}")
