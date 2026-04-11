"""Unit tests for fibonacci module."""

import pytest
from fibonacci import fibonacci


class TestEdgeCases:
    """Test edge cases for fibonacci function."""

    def test_fibonacci_zero(self):
        """F(0) should return 0."""
        assert fibonacci(0) == 0

    def test_fibonacci_one(self):
        """F(1) should return 1."""
        assert fibonacci(1) == 1

    def test_fibonacci_negative_raises(self):
        """Negative input should raise ValueError."""
        with pytest.raises(ValueError, match="non-negative integer"):
            fibonacci(-1)

    def test_fibonacci_negative_fifty(self):
        """Negative input -50 should raise ValueError."""
        with pytest.raises(ValueError):
            fibonacci(-50)


class TestKnownValues:
    """Test fibonacci against known Fibonacci numbers."""

    def test_fibonacci_two(self):
        """F(2) should return 1."""
        assert fibonacci(2) == 1

    def test_fibonacci_three(self):
        """F(3) should return 2."""
        assert fibonacci(3) == 2

    def test_fibonacci_ten(self):
        """F(10) should return 55."""
        assert fibonacci(10) == 55

    def test_fibonacci_twenty(self):
        """F(20) should return 6765."""
        assert fibonacci(20) == 6765

    def test_fibonacci_twentyfive(self):
        """F(25) should return 75025."""
        assert fibonacci(25) == 75025


class TestSequenceProperty:
    """Test that the sequence property F(n) = F(n-1) + F(n-2) holds."""

    @pytest.mark.parametrize("n", range(2, 30))
    def test_recurrence_relation(self, n):
        """Verify F(n) = F(n-1) + F(n-2) for n >= 2."""
        assert fibonacci(n) == fibonacci(n - 1) + fibonacci(n - 2)


class TestLargeInputs:
    """Test fibonacci with larger inputs to verify efficiency."""

    def test_fibonacci_hundred(self):
        """F(100) should compute efficiently."""
        assert fibonacci(100) == 354224848179261915075

    def test_fibonacci_thousand(self):
        """F(1000) should compute efficiently."""
        assert fibonacci(1000) == 43466557686937456435688527675040625802564660517371780402481729089536555417949051890403879840079255169295922593080322634775209689623239873322471161642996440906533187938298969649928516003704476137795166849228875
