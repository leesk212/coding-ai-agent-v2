"""Fibonacci sequence implementations with iterative and recursive approaches.

This module provides multiple implementations of the Fibonacci sequence
calculation, including an iterative approach and a recursive approach with
memoization for improved performance.
"""

from typing import Dict


class FibonacciError(Exception):
    """Custom exception for Fibonacci calculation errors."""

    pass


def fibonacci_iterative(n: int) -> int:
    """Calculate the nth Fibonacci number using an iterative approach.

    The Fibonacci sequence is a series of numbers where each number is the
    sum of the two preceding ones, starting from 0 and 1:
    F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2) for n > 1

    Args:
        n: The position in the Fibonacci sequence (0-indexed).

    Returns:
        The nth Fibonacci number.

    Raises:
        FibonacciError: If n is negative.

    Examples:
        >>> fibonacci_iterative(0)
        0
        >>> fibonacci_iterative(1)
        1
        >>> fibonacci_iterative(10)
        55
        >>> fibonacci_iterative(50)
        12586269025
    """
    if n < 0:
        raise FibonacciError(f"n must be non-negative, got {n}")

    if n == 0:
        return 0
    if n == 1:
        return 1

    prev: int = 0
    curr: int = 1

    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr

    return curr


def fibonacci_recursive(n: int, memo: Dict[int, int] | None = None) -> int:
    """Calculate the nth Fibonacci number using recursion with memoization.

    The Fibonacci sequence is a series of numbers where each number is the
    sum of the two preceding ones, starting from 0 and 1:
    F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2) for n > 1

    This implementation uses memoization to cache previously computed values,
    improving performance from O(2^n) to O(n) time complexity.

    Args:
        n: The position in the Fibonacci sequence (0-indexed).
        memo: Optional dictionary for memoization. If not provided, a new
              dictionary will be created.

    Returns:
        The nth Fibonacci number.

    Raises:
        FibonacciError: If n is negative.

    Examples:
        >>> fibonacci_recursive(0)
        0
        >>> fibonacci_recursive(1)
        1
        >>> fibonacci_recursive(10)
        55
        >>> fibonacci_recursive(50)
        12586269025
    """
    if n < 0:
        raise FibonacciError(f"n must be non-negative, got {n}")

    if memo is None:
        memo: Dict[int, int] = {}

    if n in memo:
        return memo[n]

    if n == 0:
        memo[0] = 0
        return 0
    if n == 1:
        memo[1] = 1
        return 1

    result: int = fibonacci_recursive(n - 1, memo) + fibonacci_recursive(
        n - 2, memo
    )
    memo[n] = result
    return result


def fibonacci_with_validation(n: int) -> int:
    """Calculate the nth Fibonacci number with input validation.

    This is a wrapper function that validates input before computing
    the Fibonacci number using the iterative approach.

    Args:
        n: The position in the Fibonacci sequence (0-indexed).

    Returns:
        The nth Fibonacci number.

    Raises:
        FibonacciError: If n is not an integer or is negative.

    Examples:
        >>> fibonacci_with_validation(0)
        0
        >>> fibonacci_with_validation(1)
        1
        >>> fibonacci_with_validation(7)
        13
    """
    if not isinstance(n, int):
        raise FibonacciError(
            f"n must be an integer, got {type(n).__name__}"
        )

    if n < 0:
        raise FibonacciError(f"n must be non-negative, got {n}")

    return fibonacci_iterative(n)


if __name__ == "__main__":
    print("Fibonacci Sequence Examples")
    print("=" * 50)

    # Test cases for iterative approach
    print("\nIterative Approach:")
    for i in range(11):
        print(f"F({i:2d}) = {fibonacci_iterative(i)}")

    # Test cases for recursive with memoization approach
    print("\nRecursive Approach (with memoization):")
    for i in range(11):
        print(f"F({i:2d}) = {fibonacci_recursive(i)}")

    # Compare performance on larger values
    print("\nLarger Fibonacci Numbers:")
    test_values: list[int] = [20, 30, 40]
    for n in test_values:
        iter_result: int = fibonacci_iterative(n)
        rec_result: int = fibonacci_recursive(n)
        print(
            f"F({n}) - Iterative: {iter_result}, "
            f"Recursive: {rec_result}"
        )

    # Demonstrate error handling
    print("\nError Handling Examples:")
    try:
        fibonacci_iterative(-5)
    except FibonacciError as e:
        print(f"Caught expected error: {e}")

    try:
        fibonacci_with_validation("10")
    except FibonacciError as e:
        print(f"Caught expected error: {e}")

    # Demonstrate memoization sharing
    print("\nMemoization Example:")
    shared_memo: Dict[int, int] = {}
    print(f"F(5) with shared memo: {fibonacci_recursive(5, shared_memo)}")
    print(f"F(7) with shared memo (faster): {fibonacci_recursive(7, shared_memo)}")
    print(f"Memo cache contents: {shared_memo}")
