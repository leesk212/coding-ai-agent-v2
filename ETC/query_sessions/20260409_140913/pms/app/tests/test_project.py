"""프로젝트 테스트"""

import pytest
from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.models import User, Project
from app.utils.security import get_password_hash
from fastapi.testclient import TestClient
from app.db import Base


class TestProjectCreation:
    """프로젝트 생성 테스트"""
    
    def test_create_project_success(self, client: TestClient, db_session: Session):
        """정상적으로 프로젝트를 생성합니다"""
        # 테스트 사용자 생성 및 로그인
        user = User(
            email="projectuser@example.com",
            password=get_password_hash("projectpassword123"),
            name="Project User"
        )
        db_session.add(user)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "projectuser@example.com",
                "password": "projectpassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 프로젝트 생성
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "Test Project",
                "code": "TP001",
                "client": "Test Client Inc.",
                "designer": "John Designer",
                "start_date": "2026-04-09",
                "end_date": "2026-06-09",
                "status": "planning"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["code"] == "TP001"
        assert data["client"] == "Test Client Inc."
        assert data["status"] == "planning"
        assert data["creator_id"] == user.id
    
    def test_create_project_invalid_dates(self, client: TestClient, db_session: Session):
        """종료일이 시작일 이전이면 생성 실패"""
        # 테스트 사용자 생성 및 로그인
        user = User(
            email="dateuser@example.com",
            password=get_password_hash("datepassword123"),
            name="Date User"
        )
        db_session.add(user)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "dateuser@example.com",
                "password": "datepassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 프로젝트 생성 (종료일이 시작일 이전)
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "Invalid Project",
                "code": "IP001",
                "client": "Invalid Client",
                "designer": "Jane Designer",
                "start_date": "2026-06-09",
                "end_date": "2026-04-09",
                "status": "planning"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422
    
    def test_create_project_missing_required_fields(self, client: TestClient, db_session: Session):
        """필수 필드가 없으면 생성 실패"""
        # 테스트 사용자 생성 및 로그인
        user = User(
            email="missinguser@example.com",
            password=get_password_hash("missingpassword123"),
            name="Missing User"
        )
        db_session.add(user)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "missinguser@example.com",
                "password": "missingpassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 필수 필드가 누락된 프로젝트 생성
        response = client.post(
            "/api/v1/projects",
            json={
                "name": "",  # 빈 이름
                "code": "MP001"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 422


class TestProjectRead:
    """프로젝트 조회 테스트"""
    
    def test_get_project_success(self, client: TestClient, db_session: Session):
        """정상적으로 프로젝트를 조회합니다"""
        # 테스트 사용자 및 프로젝트 생성
        user = User(
            email="readuser@example.com",
            password=get_password_hash("readpassword123"),
            name="Read User"
        )
        db_session.add(user)
        db_session.commit()
        
        project = Project(
            name="Read Project",
            code="RP001",
            client="Read Client",
            designer="Read Designer",
            start_date=date(2026, 4, 9),
            end_date=date(2026, 6, 9),
            status="planning",
            creator_id=user.id
        )
        db_session.add(project)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "readuser@example.com",
                "password": "readpassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 프로젝트 조회
        response = client.get(
            f"/api/v1/projects/{project.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == project.id
        assert data["name"] == "Read Project"
    
    def test_get_project_not_found(self, client: TestClient, db_session: Session):
        """존재하지 않는 프로젝트를 조회하면 404"""
        # 테스트 사용자 생성 및 로그인
        user = User(
            email="notfounduser@example.com",
            password=get_password_hash("notfoundpassword123"),
            name="Not Found User"
        )
        db_session.add(user)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "notfounduser@example.com",
                "password": "notfoundpassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 존재하지 않는 프로젝트 조회
        response = client.get(
            "/api/v1/projects/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
    
    def test_list_projects(self, client: TestClient, db_session: Session):
        """프로젝트 목록을 조회합니다"""
        # 테스트 사용자 및 프로젝트 생성
        user = User(
            email="listuser@example.com",
            password=get_password_hash("listpassword123"),
            name="List User"
        )
        db_session.add(user)
        db_session.commit()
        
        # 여러 프로젝트 생성
        for i in range(3):
            project = Project(
                name=f"List Project {i+1}",
                code=f"LP{i+1:03d}",
                client="List Client",
                designer="List Designer",
                start_date=date(2026, 4, 9),
                end_date=date(2026, 6, 9),
                status="planning",
                creator_id=user.id
            )
            db_session.add(project)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "listuser@example.com",
                "password": "listpassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 프로젝트 목록 조회
        response = client.get(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 3
        assert len(data["items"]) >= 3


class TestProjectUpdate:
    """프로젝트 수정 테스트"""
    
    def test_update_project_success(self, client: TestClient, db_session: Session):
        """정상적으로 프로젝트를 수정합니다"""
        # 테스트 사용자 및 프로젝트 생성
        user = User(
            email="updateuser@example.com",
            password=get_password_hash("updatepassword123"),
            name="Update User"
        )
        db_session.add(user)
        db_session.commit()
        
        project = Project(
            name="Original Name",
            code="UP001",
            client="Original Client",
            designer="Original Designer",
            start_date=date(2026, 4, 9),
            end_date=date(2026, 6, 9),
            status="planning",
            creator_id=user.id
        )
        db_session.add(project)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "updateuser@example.com",
                "password": "updatepassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 프로젝트 수정
        response = client.put(
            f"/api/v1/projects/{project.id}",
            json={
                "name": "Updated Name",
                "client": "Updated Client"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["client"] == "Updated Client"
        assert data["code"] == "UP001"  # 수정하지 않은 필드는 유지됨
    
    def test_update_project_not_found(self, client: TestClient, db_session: Session):
        """존재하지 않는 프로젝트를 수정하면 404"""
        # 테스트 사용자 생성 및 로그인
        user = User(
            email="updatenotfounduser@example.com",
            password=get_password_hash("updatenotfoundpassword123"),
            name="Update Not Found User"
        )
        db_session.add(user)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "updatenotfounduser@example.com",
                "password": "updatenotfoundpassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 존재하지 않는 프로젝트 수정
        response = client.put(
            "/api/v1/projects/99999",
            json={"name": "Updated Name"},
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404


class TestProjectDelete:
    """프로젝트 삭제 테스트"""
    
    def test_delete_project_success(self, client: TestClient, db_session: Session):
        """정상적으로 프로젝트를 삭제합니다"""
        # 테스트 사용자 및 프로젝트 생성
        user = User(
            email="deleteuser@example.com",
            password=get_password_hash("deletepassword123"),
            name="Delete User"
        )
        db_session.add(user)
        db_session.commit()
        
        project = Project(
            name="Delete Project",
            code="DP001",
            client="Delete Client",
            designer="Delete Designer",
            start_date=date(2026, 4, 9),
            end_date=date(2026, 6, 9),
            status="planning",
            creator_id=user.id
        )
        db_session.add(project)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "deleteuser@example.com",
                "password": "deletepassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 프로젝트 삭제
        response = client.delete(
            f"/api/v1/projects/{project.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 204
        
        # 프로젝트가 삭제되었는지 확인
        get_response = client.get(
            f"/api/v1/projects/{project.id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert get_response.status_code == 404
    
    def test_delete_project_not_found(self, client: TestClient, db_session: Session):
        """존재하지 않는 프로젝트를 삭제하면 404"""
        # 테스트 사용자 생성 및 로그인
        user = User(
            email="deleteusernotfound@example.com",
            password=get_password_hash("deleteusernotfoundpassword123"),
            name="Delete User Not Found"
        )
        db_session.add(user)
        db_session.commit()
        
        login_response = client.post(
            "/api/v1/auth/login",
            data={
                "username": "deleteusernotfound@example.com",
                "password": "deleteusernotfoundpassword123"
            }
        )
        token = login_response.json()["access_token"]
        
        # 존재하지 않는 프로젝트 삭제
        response = client.delete(
            "/api/v1/projects/99999",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        assert response.status_code == 404
