"""메인 FastAPI 애플리케이션"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.db import engine, Base
from app.routers import auth, projects

# 데이터베이스 테이블 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="PMS",
    description="프로젝트 관리 시스템 API",
    version="0.1.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(projects.router, prefix=settings.API_V1_PREFIX)


@app.get("/")
def read_root():
    """
    루트 엔드포인트
    
    Returns:
        dict: 애플리케이션 정보
    """
    return {
        "message": "PMS API 서버",
        "version": "0.1.0",
        "docs": f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else "Disabled"
    }


@app.get("/health")
def health_check():
    """
    헬스 체크 엔드포인트
    
    Returns:
        dict: 서버 상태
    """
    return {"status": "healthy"}
