"""Fibonacci sequence module with efficient calculation and input validation."""


def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    The Fibonacci sequence is a series of numbers where each number is the sum
    of the two preceding ones, starting from 0 and 1:

    F(0) = 0
    F(1) = 1
    F(n) = F(n-1) + F(n-2) for n > 1

    Args:
        n: The position in the Fibonacci sequence (0-indexed). Must be a
            non-negative integer.

    Returns:
        The nth Fibonacci number as an integer.

    Raises:
        ValueError: If n is negative.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
        >>> fibonacci(-1)
        Traceback (most recent call last):
            ...
        ValueError: n must be a non-negative integer
    """
    if n < 0:
        raise ValueError("n must be a non-negative integer")

    if n == 0:
        return 0

    if n == 1:
        return 1

    previous_value: int = 0
    current_value: int = 1

    for _ in range(2, n + 1):
        next_value: int = previous_value + current_value
        previous_value = current_value
        current_value = next_value

    return current_value


if __name__ == "__main__":
    print("Fibonacci Sequence Calculator")
    print("=" * 40)

    # Edge case examples
    print("\nEdge Cases:")
    print(f"fibonacci(0) = {fibonacci(0)}")
    print(f"fibonacci(1) = {fibonacci(1)}")

    # Standard examples
    print("\nFirst 15 Fibonacci Numbers:")
    for i in range(15):
        print(f"fibonacci({i}) = {fibonacci(i)}")

    # Error handling example
    print("\nError Handling:")
    try:
        fibonacci(-5)
    except ValueError as e:
        print(f"fibonacci(-5) raised ValueError: {e}")
