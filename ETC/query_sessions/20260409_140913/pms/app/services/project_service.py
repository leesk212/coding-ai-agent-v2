"""프로젝트 서비스"""

from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import Project, ProjectStatus, User, UserRole
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.utils.security import get_current_admin_user


class ProjectService:
    """
    프로젝트 서비스
    
    프로젝트 관련 비즈니스 로직을 처리합니다.
    """
    
    @staticmethod
    def create_project(
        db: Session,
        project: ProjectCreate,
        creator_id: int
    ) -> Project:
        """
        새 프로젝트를 생성합니다.
        
        Args:
            db: 데이터베이스 세션
            project: 프로젝트 생성 데이터
            creator_id: 생성자 ID
            
        Returns:
            Project: 생성된 프로젝트
        """
        db_project = Project(
            name=project.name,
            code=project.code,
            client=project.client,
            designer=project.designer,
            start_date=project.start_date,
            end_date=project.end_date,
            status=project.status,
            description=project.description,
            creator_id=creator_id
        )
        
        db.add(db_project)
        db.commit()
        db.refresh(db_project)
        
        return db_project
    
    @staticmethod
    def get_project(db: Session, project_id: int) -> Optional[Project]:
        """
        ID 로 프로젝트를 조회합니다.
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            
        Returns:
            Optional[Project]: 프로젝트 또는 None
        """
        return db.query(Project).filter(Project.id == project_id).first()
    
    @staticmethod
    def get_projects_by_creator(
        db: Session,
        user_id: int,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        """
        생성자의 프로젝트를 조회합니다.
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
            skip: 건너뛸 항목 수
            limit: 반환할 최대 항목 수
            
        Returns:
            List[Project]: 프로젝트 목록
        """
        return db.query(Project).filter(
            Project.creator_id == user_id
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_all_projects(
        db: Session,
        status: Optional[ProjectStatus] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Project]:
        """
        모든 프로젝트를 조회합니다 (관리자용).
        
        Args:
            db: 데이터베이스 세션
            status: 상태 필터 (선택)
            skip: 건너뛸 항목 수
            limit: 반환할 최대 항목 수
            
        Returns:
            List[Project]: 프로젝트 목록
        """
        query = db.query(Project)
        if status:
            query = query.filter(Project.status == status)
        return query.offset(skip).limit(limit).all()
    
    @staticmethod
    def update_project(
        db: Session,
        project_id: int,
        project_update: ProjectUpdate,
        user: User
    ) -> Optional[Project]:
        """
        프로젝트를 업데이트합니다.
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            project_update: 업데이트 데이터
            user: 업데이트 수행 사용자
            
        Returns:
            Optional[Project]: 업데이트된 프로젝트 또는 None
        """
        db_project = db.query(Project).filter(Project.id == project_id).first()
        if not db_project:
            return None
        
        # 권한 체크: 생성자 또는 관리자만 수정 가능
        if (db_project.creator_id != user.id and 
            user.role != UserRole.ADMIN):
            raise PermissionError("Not authorized to update this project")
        
        # 업데이트할 필드만 업데이트
        update_data = project_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_project, field, value)
        
        db_project.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(db_project)
        
        return db_project
    
    @staticmethod
    def delete_project(db: Session, project_id: int, user: User) -> bool:
        """
        프로젝트를 삭제합니다.
        
        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            user: 삭제 수행 사용자
            
        Returns:
            bool: 삭제 성공 여부
        """
        db_project = db.query(Project).filter(Project.id == project_id).first()
        if not db_project:
            return False
        
        # 권한 체크: 생성자 또는 관리자만 삭제 가능
        if (db_project.creator_id != user.id and 
            user.role != UserRole.ADMIN):
            raise PermissionError("Not authorized to delete this project")
        
        db.delete(db_project)
        db.commit()
        
        return True
    
    @staticmethod
    def get_project_statistics(db: Session, user_id: int) -> dict:
        """
        프로젝트 통계를 가져옵니다.
        
        Args:
            db: 데이터베이스 세션
            user_id: 사용자 ID
            
        Returns:
            dict: 통계 데이터
        """
        projects = db.query(Project).filter(Project.creator_id == user_id).all()
        
        total = len(projects)
        planning = sum(1 for p in projects if p.status == ProjectStatus.PLANNING)
        in_progress = sum(1 for p in projects if p.status == ProjectStatus.IN_PROGRESS)
        completed = sum(1 for p in projects if p.status == ProjectStatus.COMPLETED)
        on_hold = sum(1 for p in projects if p.status == ProjectStatus.ON_HOLD)
        
        return {
            "total": total,
            "planning": planning,
            "in_progress": in_progress,
            "completed": completed,
            "on_hold": on_hold
        }
