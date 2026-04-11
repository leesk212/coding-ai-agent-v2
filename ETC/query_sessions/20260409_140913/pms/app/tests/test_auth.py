"""사용자 인증 테스트"""

import pytest
from sqlalchemy.orm import Session
from app.models import User
from app.utils.security import get_password_hash
from fastapi.testclient import TestClient
from app.db import Base


class TestUserRegistration:
    """사용자 등록 테스트"""
    
    def test_register_user_success(self, client: TestClient):
        """정상적으로 사용자를 등록합니다"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepassword123",
                "name": "New User"
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "newuser@example.com"
        assert data["name"] == "New User"
        assert "id" in data
        assert "password" not in data  # 비밀번호는 반환되지 않아야 함
    
    def test_register_user_invalid_email(self, client: TestClient):
        """잘못된 이메일 형식으로 등록 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "securepassword123",
                "name": "Invalid User"
            }
        )
        
        assert response.status_code == 422
    
    def test_register_user_password_too_short(self, client: TestClient):
        """비밀번호가 너무 짧으면 등록 실패"""
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "shortpass@example.com",
                "password": "short",
                "name": "Short Pass User"
            }
        )
        
        assert response.status_code == 422
    
    def test_register_duplicate_email(self, client: TestClient, db_session: Session):
        """중복된 이메일로 등록 실패"""
        # 기존 사용자 생성
        existing_user = User(
            email="duplicate@example.com",
            password=get_password_hash("existingpassword"),
            name="Existing User"
        )
        db_session.add(existing_user)
        db_session.commit()
        
        # 같은 이메일로 다시 등록 시도
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "newpassword",
                "name": "New Duplicate User"
            }
        )
        
        assert response.status_code == 400
        assert "already registered" in response.json()["detail"].lower()


class TestUserLogin:
    """사용자 로그인 테스트"""
    
    def test_login_success(self, client: TestClient, db_session: Session):
        """정상적으로 로그인 성공"""
        # 테스트 사용자 생성
        user = User(
            email="login@example.com",
            password=get_password_hash("loginpassword123"),
            name="Login User"
        )
        db_session.add(user)
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "login@example.com",
                "password": "loginpassword123"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "expires_in" in data
    
    def test_login_invalid_password(self, client: TestClient, db_session: Session):
        """잘못된 비밀번호로 로그인 실패"""
        # 테스트 사용자 생성
        user = User(
            email="wrongpass@example.com",
            password=get_password_hash("correctpassword123"),
            name="Wrong Pass User"
        )
        db_session.add(user)
        db_session.commit()
        
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "wrongpass@example.com",
                "password": "wrongpassword"
            }
        )
        
        assert response.status_code == 401
    
    def test_login_user_not_found(self, client: TestClient):
        """존재하지 않는 사용자로 로그인 실패"""
        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "notexist@example.com",
                "password": "somepassword"
            }
        )
        
        assert response.status_code == 401


class TestGetCurrentUser:
    """현재 사용자 정보 조회 테스트"""
    
    def test_get_current_user_success(self, client: TestClient, db_session: Session):
        """정상적으로 현재 사용자 정보 조회"""
        # 테스트 사용자 생성
        user = User(
            email="currentuser@example.com",
            password=get_password_hash("currentpassword123"),
            name="Current User"
        )
        db_session.add(user)
        db_session.commit()
        
        # 로그인
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "currentuser@example.com",
                "password": "currentpassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 현재 사용자 정보 조회
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "currentuser@example.com"
        assert data["name"] == "Current User"
    
    def test_get_current_user_invalid_token(self, client: TestClient):
        """잘못된 토큰으로 조회 실패"""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid_token"}
        )
        
        assert response.status_code == 401
