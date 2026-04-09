"""
단위 테스트: 환불 계산기 모듈

이 파일은 refund_calculator 모듈에 대한 pytest 기반 단위 테스트를 포함한다.
"""

import pytest
from typing import Tuple

from refund_calculator import (
    RefundCalculator,
    CustomerTier,
    refund_calculator,
)


class TestRefundCalculator:
    """RefundCalculator 클래스에 대한 단위 테스트"""
    
    @pytest.fixture
    def calculator(self) -> RefundCalculator:
        """RefundCalculator 인스턴스를 반환하는 fixture"""
        return RefundCalculator()
    
    @pytest.mark.parametrize(
        "tier,expected_rate",
        [
            (CustomerTier.BRONZE, 0.10),
            (CustomerTier.SILVER, 0.00),
            (CustomerTier.GOLD, 0.00),
        ],
    )
    def test_get_fee_rate(
        self,
        calculator: RefundCalculator,
        tier: CustomerTier,
        expected_rate: float
    ) -> None:
        """등급별 수수료 비율 반환 테스트"""
        assert calculator.get_fee_rate(tier) == expected_rate
    
    @pytest.mark.parametrize(
        "amount,tier,expected_refund",
        [
            # 100,000원 기본 케이스
            (100000, CustomerTier.BRONZE, 90000.0),
            (100000, CustomerTier.SILVER, 100000.0),
            (100000, CustomerTier.GOLD, 100000.0),
            # 소수점 처리
            (99999, CustomerTier.BRONZE, 89999.1),
            (99999, CustomerTier.SILVER, 99999.0),
            # 0 원
            (0, CustomerTier.BRONZE, 0.0),
            (0, CustomerTier.SILVER, 0.0),
            (0, CustomerTier.GOLD, 0.0),
        ],
    )
    def test_calculate_refund_amount(
        self,
        calculator: RefundCalculator,
        amount: float,
        tier: CustomerTier,
        expected_refund: float
    ) -> None:
        """환불 금액 계산 테스트"""
        result = calculator.calculate_refund_amount(amount, tier)
        assert result == expected_refund, f"Expected {expected_refund}, got {result}"
    
    @pytest.mark.parametrize(
        "amount,tier,expected_fee",
        [
            (100000, CustomerTier.BRONZE, 10000.0),
            (100000, CustomerTier.SILVER, 0.0),
            (100000, CustomerTier.GOLD, 0.0),
            (50000, CustomerTier.BRONZE, 5000.0),
        ],
    )
    def test_calculate_fee_amount(
        self,
        calculator: RefundCalculator,
        amount: float,
        tier: CustomerTier,
        expected_fee: float
    ) -> None:
        """수수료 금액 계산 테스트"""
        result = calculator.calculate_fee_amount(amount, tier)
        assert result == expected_fee, f"Expected {expected_fee}, got {result}"
    
    def test_calculate_refund_amount_invalid(self) -> None:
        """잘못된 입력에 대한 예외 처리 테스트"""
        calculator = RefundCalculator()
        with pytest.raises(ValueError, match="결제 금액은 0 이상이어야 합니다"):
            calculator.calculate_refund_amount(-1000, CustomerTier.SILVER)
    
    def test_singleton_instance(self) -> None:
        """공유 인스턴스 존재 확인 테스트"""
        assert isinstance(refund_calculator, RefundCalculator)


# 테스트 실행 시나리오
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
