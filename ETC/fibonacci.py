"""Fibonacci sequence implementation with comprehensive error handling.

This module provides a function to calculate the nth Fibonacci number
with proper type checking and documentation.
"""

from typing import Union


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    The Fibonacci sequence starts with 0 and 1, where each subsequent
    number is the sum of the two preceding numbers: 0, 1, 1, 2, 3, 5, 8, ...

    Args:
        n: The position in the Fibonacci sequence (0-indexed).
           Must be a non-negative integer.

    Returns:
        The nth Fibonacci number.

    Raises:
        TypeError: If n is not an integer type.
        ValueError: If n is a negative number.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
    """
    # Validate input type - explicitly check for bool since bool is subclass of int
    if isinstance(n, bool) or not isinstance(n, int):
        raise TypeError(f"Expected int type, got {type(n).__name__}")

    # Validate input value - negative numbers are not defined in this implementation
    if n < 0:
        raise ValueError(f"Fibonacci is not defined for negative numbers: {n}")

    # Base cases: F(0) = 0, F(1) = 1
    # These are the first two numbers in the Fibonacci sequence
    if n == 0:
        return 0
    if n == 1:
        return 1

    # Iterative calculation using space-optimized approach
    # We only need the last two values to compute the next one
    # Time complexity: O(n), Space complexity: O(1)
    prev: int = 0  # F(i-2), initially F(0)
    curr: int = 1  # F(i-1), initially F(1)

    # Iterate from position 2 to n
    # Each iteration computes F(i) = F(i-1) + F(i-2)
    for _ in range(2, n + 1):
        # Calculate next Fibonacci number
        next_val: int = prev + curr
        # Update previous and current values for next iteration
        prev = curr
        curr = next_val

    return curr


if __name__ == "__main__":
    # Test cases demonstrating correctness
    print("Running Fibonacci test cases...")
    print("-" * 40)

    # Test Case 1: Base case - F(0) should return 0
    result_0 = fibonacci(0)
    assert result_0 == 0, f"Test 1 failed: expected 0, got {result_0}"
    print(f"✓ Test 1 passed: fibonacci(0) = {result_0}")

    # Test Case 2: Base case - F(1) should return 1
    result_1 = fibonacci(1)
    assert result_1 == 1, f"Test 2 failed: expected 1, got {result_1}"
    print(f"✓ Test 2 passed: fibonacci(1) = {result_1}")

    # Test Case 3: General case - F(10) should return 55
    # Sequence: 0, 1, 1, 2, 3, 5, 8, 13, 21, 34, 55
    result_10 = fibonacci(10)
    assert result_10 == 55, f"Test 3 failed: expected 55, got {result_10}"
    print(f"✓ Test 3 passed: fibonacci(10) = {result_10}")

    print("-" * 40)
    print("All tests passed!")

    # Additional verification with known values
    print("\nAdditional verification:")
    print(f"fibonacci(5) = {fibonacci(5)} (expected: 5)")
    print(f"fibonacci(7) = {fibonacci(7)} (expected: 13)")
    print(f"fibonacci(15) = {fibonacci(15)} (expected: 610)")
