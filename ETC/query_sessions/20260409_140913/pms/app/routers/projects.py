"""프로젝트 라우터"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db import get_db
from app.schemas import ProjectCreate, ProjectUpdate, ProjectResponse, ProjectListResponse, GanttChartData
from app.models import ProjectStatus, User
from app.services.project_service import ProjectService
from app.utils.security import get_current_user, get_current_admin_user

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
def create_project(
    project: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    새 프로젝트를 생성합니다.
    
    Args:
        project: 프로젝트 생성 정보
        db: 데이터베이스 세션
        current_user: 인증된 현재 사용자
        
    Returns:
        ProjectResponse: 생성된 프로젝트 정보
    """
    db_project = ProjectService.create_project(db, project, current_user.id)
    return db_project


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    단일 프로젝트를 조회합니다.
    
    Args:
        project_id: 프로젝트 ID
        db: 데이터베이스 세션
        current_user: 인증된 현재 사용자
        
    Returns:
        ProjectResponse: 프로젝트 정보
        
    Raises:
        HTTPException: 프로젝트를 찾을 수 없는 경우
    """
    db_project = ProjectService.get_project(db, project_id)
    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    return db_project


@router.get("", response_model=ProjectListResponse)
def list_projects(
    skip: int = Query(0, ge=0, description="건너뛸 항목 수"),
    limit: int = Query(100, ge=1, le=1000, description="반환할 최대 항목 수"),
    status: Optional[ProjectStatus] = Query(None, description="프로젝트 상태 필터"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    프로젝트 목록을 조회합니다.
    
    Args:
        skip: 건너뛸 항목 수
        limit: 반환할 최대 항목 수
        status: 상태 필터 (선택)
        db: 데이터베이스 세션
        current_user: 인증된 현재 사용자
        
    Returns:
        ProjectListResponse: 프로젝트 목록
    """
    # 관리자는 모든 프로젝트 조회, 일반 사용자는 자신의 프로젝트만
    if current_user.role == "admin":
        projects = ProjectService.get_all_projects(db, status=status, skip=skip, limit=limit)
        total = len(projects)
    else:
        projects = ProjectService.get_projects_by_creator(db, current_user.id, skip=skip, limit=limit)
        total = len(projects)
    
    return ProjectListResponse(
        total=total,
        items=projects
    )


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    프로젝트를 업데이트합니다.
    
    Args:
        project_id: 프로젝트 ID
        project_update: 업데이트 정보
        db: 데이터베이스 세션
        current_user: 인증된 현재 사용자
        
    Returns:
        ProjectResponse: 업데이트된 프로젝트 정보
        
    Raises:
        HTTPException: 프로젝트를 찾을 수 없는 경우
    """
    try:
        db_project = ProjectService.update_project(db, project_id, project_update, current_user)
        if not db_project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found"
            )
        return db_project
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    프로젝트를 삭제합니다.
    
    Args:
        project_id: 프로젝트 ID
        db: 데이터베이스 세션
        current_user: 인증된 현재 사용자
        
    Raises:
        HTTPException: 프로젝트를 찾을 수 없거나 권한이 없는 경우
    """
    success = ProjectService.delete_project(db, project_id, current_user)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )


@router.get("/{project_id}/gantt", response_model=GanttChartData)
def get_gantt_chart(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    프로젝트의 간트 차트 데이터를 가져옵니다.
    
    Args:
        project_id: 프로젝트 ID
        db: 데이터베이스 세션
        current_user: 인증된 현재 사용자
        
    Returns:
        GanttChartData: 간트 차트 데이터
        
    Raises:
        HTTPException: 프로젝트를 찾을 수 없는 경우
    """
    from app.models import Task
    
    db_project = ProjectService.get_project(db, project_id)
    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # 프로젝트 태스크 조회
    tasks = db.query(Task).filter(Task.project_id == project_id).all()
    
    gantt_tasks = [
        GanttChartEntry(
            id=t.id,
            name=t.name,
            start_date=t.start_date,
            end_date=t.end_date,
            progress=t.progress,
            status=t.status,
            assignee_id=t.assignee_id,
            parent_id=t.parent_task_id
        )
        for t in tasks
    ]
    
    return GanttChartData(
        project_id=project_id,
        project_name=db_project.name,
        project_start=db_project.start_date,
        project_end=db_project.end_date,
        tasks=gantt_tasks
    )


@router.get("/{project_id}/statistics", response_model=dict)
def get_project_statistics(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    프로젝트 통계를 가져옵니다.
    
    Args:
        project_id: 프로젝트 ID
        db: 데이터베이스 세션
        current_user: 인증된 현재 사용자
        
    Returns:
        dict: 통계 데이터
        
    Raises:
        HTTPException: 프로젝트를 찾을 수 없는 경우
    """
    db_project = ProjectService.get_project(db, project_id)
    if not db_project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # 해당 프로젝트의 태스크 통계
    from app.models import Task, ProjectStatus as TaskStatus
    
    total_tasks = db.query(Task).filter(Task.project_id == project_id).count()
    planning = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status == TaskStatus.PLANNING
    ).count()
    in_progress = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status == TaskStatus.IN_PROGRESS
    ).count()
    completed = db.query(Task).filter(
        Task.project_id == project_id,
        Task.status == TaskStatus.COMPLETED
    ).count()
    
    return {
        "project_id": project_id,
        "total_tasks": total_tasks,
        "planning": planning,
        "in_progress": in_progress,
        "completed": completed
    }
