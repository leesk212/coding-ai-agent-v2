"""
고객 등급별 환불 수수료 계산 모듈

이 모듈은 고객 등급에 따라 다른 환불 수수료를 적용하는 로직을 제공한다.
"""

from enum import Enum
from typing import Dict, Union


class CustomerTier(Enum):
    """고객 등급 열거형"""
    BRONZE = "bronze"
    SILVER = "silver"
    GOLD = "gold"


class RefundCalculator:
    """환불 수수료 계산기"""
    
    # 등급별 수수료 비율 (소수점)
    FEE_RATES: Dict[CustomerTier, float] = {
        CustomerTier.BRONZE: 0.10,  # 10%
        CustomerTier.SILVER: 0.00,  # 0%
        CustomerTier.GOLD: 0.00,    # 0%
    }
    
    @classmethod
    def get_fee_rate(cls, tier: CustomerTier) -> float:
        """
        주어진 고객 등급의 수수료 비율을 반환한다.
        
        Args:
            tier: 고객 등급
            
        Returns:
            수수료 비율 (0.0 ~ 1.0)
        """
        return cls.FEE_RATES.get(tier, 0.0)
    
    def calculate_refund_amount(
        self,
        original_amount: float,
        tier: CustomerTier
    ) -> float:
        """
        고객 등급을 적용한 환불 금액을 계산한다.
        
        Args:
            original_amount: 원래 결제 금액
            tier: 고객 등급
            
        Returns:
            실제 환불 받을 금액 (원)
        """
        if original_amount < 0:
            raise ValueError("결제 금액은 0 이상이어야 합니다")
        
        fee_rate = self.get_fee_rate(tier)
        fee_amount = original_amount * fee_rate
        refund_amount = original_amount - fee_amount
        
        return round(refund_amount, 2)
    
    def calculate_fee_amount(
        self,
        original_amount: float,
        tier: CustomerTier
    ) -> float:
        """
        고객 등급에 따른 수수료 금액을 계산한다.
        
        Args:
            original_amount: 원래 결제 금액
            tier: 고객 등급
            
        Returns:
            수수료 금액 (원)
        """
        if original_amount < 0:
            raise ValueError("결제 금액은 0 이상이어야 합니다")
        
        fee_rate = self.get_fee_rate(tier)
        fee_amount = original_amount * fee_rate
        
        return round(fee_amount, 2)


# 인스턴스 공유 (singleton 패턴)
refund_calculator = RefundCalculator()
