"""Fibonacci sequence calculator with efficient iterative implementation."""

from typing import final


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number using an efficient iterative algorithm.
    
    The Fibonacci sequence is defined as:
    - F(0) = 0
    - F(1) = 1
    - F(n) = F(n-1) + F(n-2) for n >= 2
    
    This implementation uses O(n) time complexity and O(1) space complexity.
    
    Args:
        n: The position in the Fibonacci sequence (0-indexed).
        
    Returns:
        The nth Fibonacci number.
        
    Raises:
        ValueError: If n is negative.
        
    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
    """
    if n < 0:
        raise ValueError(f"n must be non-negative, got {n}")
    
    if n == 0:
        return 0
    if n == 1:
        return 1
    
    prev: int = 0
    curr: int = 1
    
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr
    
    return curr


if __name__ == "__main__":
    print("Fibonacci Sequence Examples:")
    print("-" * 40)
    
    for i in range(11):
        print(f"F({i}) = {fibonacci(i)}")
    
    print("-" * 40)
    print("\nEdge Cases:")
    print(f"F(0) = {fibonacci(0)}")
    print(f"F(1) = {fibonacci(1)}")
    
    try:
        fibonacci(-1)
    except ValueError as e:
        print(f"F(-1) raises ValueError: {e}")
