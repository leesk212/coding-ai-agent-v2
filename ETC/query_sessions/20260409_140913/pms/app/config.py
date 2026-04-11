"""애플리케이션 설정 관리"""

from functools import lru_cache
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """
    애플리케이션 설정 클래스
    
    환경 변수에서 설정값을 로드하며, Pydantic Settings 를 사용합니다.
    """
    
    # API 설정
    API_V1_PREFIX: str = "/api/v1"
    DEBUG: bool = True
    
    # 데이터베이스
    DATABASE_URL: str = "sqlite:///./pms.db"
    
    # JWT 설정
    SECRET_KEY: str = "super-secret-key-for-development-only-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    class Config:
        """설정 클래스 구성"""
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """
    설정을 캐시하여 반환하는 함수
    
    Returns:
        Settings: 애플리케이션 설정
        
    Note:
        @lru_cache 를 사용하여 설정 로드 오버헤드 방지
    """
    return Settings()


settings = get_settings()
