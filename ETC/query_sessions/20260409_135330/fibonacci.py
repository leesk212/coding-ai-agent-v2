"""Fibonacci sequence implementation with comprehensive error handling and tests."""

import unittest
from typing import Union


def fibonacci(n: int) -> Union[int, str]:
    """
    Calculate the nth Fibonacci number.

    The Fibonacci sequence is a series where each number is the sum of the two
    preceding ones, starting with 0 and 1:
    F(0) = 0, F(1) = 1, F(n) = F(n-1) + F(n-2) for n > 1

    Args:
        n (int): The position in the Fibonacci sequence (0-indexed).
                 Must be a non-negative integer.

    Returns:
        Union[int, str]: The nth Fibonacci number if input is valid,
                        or an error message string if input is invalid.

    Raises:
        TypeError: If n is not an integer type.
        ValueError: If n is negative.

    Examples:
        >>> fibonacci(0)
        0
        >>> fibonacci(1)
        1
        >>> fibonacci(10)
        55
        >>> fibonacci(-5)
        'Error: Input must be a non-negative integer.'
    """
    if not isinstance(n, int):
        raise TypeError("Input must be an integer.")
    if n < 0:
        raise ValueError("Input must be a non-negative integer.")

    if n == 0:
        return 0
    if n == 1:
        return 1

    prev, curr = 0, 1
    for _ in range(2, n + 1):
        prev, curr = curr, prev + curr

    return curr


class TestFibonacci(unittest.TestCase):
    """Unit tests for the fibonacci function."""

    def test_fibonacci_zero(self):
        """Test fibonacci(0) returns 0."""
        self.assertEqual(fibonacci(0), 0)

    def test_fibonacci_one(self):
        """Test fibonacci(1) returns 1."""
        self.assertEqual(fibonacci(1), 1)

    def test_fibonacci_second(self):
        """Test fibonacci(2) returns 1."""
        self.assertEqual(fibonacci(2), 1)

    def test_fibonacci_small_values(self):
        """Test fibonacci for small positive integers."""
        self.assertEqual(fibonacci(3), 2)
        self.assertEqual(fibonacci(4), 3)
        self.assertEqual(fibonacci(5), 5)
        self.assertEqual(fibonacci(6), 8)
        self.assertEqual(fibonacci(7), 13)
        self.assertEqual(fibonacci(8), 21)
        self.assertEqual(fibonacci(9), 34)
        self.assertEqual(fibonacci(10), 55)

    def test_fibonacci_larger_values(self):
        """Test fibonacci for larger indices."""
        self.assertEqual(fibonacci(20), 6765)
        self.assertEqual(fibonacci(30), 832040)
        self.assertEqual(fibonacci(50), 12586269025)

    def test_fibonacci_negative_input(self):
        """Test that negative input raises ValueError."""
        with self.assertRaises(ValueError):
            fibonacci(-1)
        with self.assertRaises(ValueError):
            fibonacci(-10)

    def test_fibonacci_non_integer_input(self):
        """Test that non-integer input raises TypeError."""
        with self.assertRaises(TypeError):
            fibonacci(3.5)
        with self.assertRaises(TypeError):
            fibonacci("5")
        with self.assertRaises(TypeError):
            fibonacci([5])
        with self.assertRaises(TypeError):
            fibonacci(None)

    def test_fibonacci_float_input(self):
        """Test that float input raises TypeError."""
        with self.assertRaises(TypeError):
            fibonacci(5.0)

    def test_fibonacci_zero_is_even_position(self):
        """Verify F(0) is at an even position and equals 0."""
        self.assertEqual(fibonacci(0), 0)
        self.assertIsInstance(fibonacci(0), int)

    def test_fibonacci_boundary_conditions(self):
        """Test boundary condition around zero."""
        # F(0) = 0, F(1) = 1, F(2) = 1
        self.assertEqual(fibonacci(0), 0)
        self.assertEqual(fibonacci(1), 1)
        self.assertEqual(fibonacci(2), 1)


if __name__ == "__main__":
    unittest.main()
