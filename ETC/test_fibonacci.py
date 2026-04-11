"""Unit tests for Fibonacci implementation."""

import pytest
from fibonacci import fibonacci, fibonacci_list


class TestFibonacci:
    """Test cases for the fibonacci function."""

    def test_fibonacci_zero(self) -> None:
        """Test fibonacci(0) returns 0."""
        assert fibonacci(0) == 0

    def test_fibonacci_one(self) -> None:
        """Test fibonacci(1) returns 1."""
        assert fibonacci(1) == 1

    def test_fibonacci_small_positive(self) -> None:
        """Test fibonacci for small positive integers."""
        assert fibonacci(2) == 1
        assert fibonacci(3) == 2
        assert fibonacci(4) == 3
        assert fibonacci(5) == 5

    def test_fibonacci_medium(self) -> None:
        """Test fibonacci for medium values."""
        assert fibonacci(10) == 55
        assert fibonacci(15) == 610
        assert fibonacci(20) == 6765

    def test_fibonacci_large(self) -> None:
        """Test fibonacci for larger values."""
        assert fibonacci(50) == 12586269025

    def test_fibonacci_negative(self) -> None:
        """Test fibonacci raises ValueError for negative input."""
        with pytest.raises(ValueError):
            fibonacci(-1)
        with pytest.raises(ValueError):
            fibonacci(-100)

    def test_fibonacci_edge_cases(self) -> None:
        """Test fibonacci edge cases."""
        assert fibonacci(0) == 0
        assert fibonacci(1) == 1


class TestFibonacciList:
    """Test cases for the fibonacci_list function."""

    def test_fibonacci_list_zero(self) -> None:
        """Test fibonacci_list(0) returns empty list."""
        assert fibonacci_list(0) == []

    def test_fibonacci_list_single(self) -> None:
        """Test fibonacci_list(1) returns single element list."""
        assert fibonacci_list(1) == [0]

    def test_fibonacci_list_multiple(self) -> None:
        """Test fibonacci_list for multiple elements."""
        assert fibonacci_list(5) == [0, 1, 1, 2, 3]
        assert fibonacci_list(10) == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

    def test_fibonacci_list_negative(self) -> None:
        """Test fibonacci_list raises ValueError for negative input."""
        with pytest.raises(ValueError):
            fibonacci_list(-1)
        with pytest.raises(ValueError):
            fibonacci_list(-10)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
