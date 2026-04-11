"""
Pydantic schemas for Project Management System.

This module provides request and response models for all API endpoints.
All models use Pydantic v2 with type hints and validation.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class UserRole(str, Enum):
    """User role enumeration."""
    PM = "PM"
    ADMIN = "ADMIN"


class ProjectStatus(str, Enum):
    """Project status enumeration."""
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    ON_HOLD = "on_hold"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskStatus(str, Enum):
    """Task status enumeration."""
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class EventType(str, Enum):
    """Timeline event type enumeration."""
    TASK_STATUS_CHANGE = "task_status_change"
    PROJECT_STATUS_CHANGE = "project_status_change"
    MILESTONE = "milestone"
    DUE_DATE = "due_date"
    ALL = "all"


# ============================================================================
# REQUEST MODELS
# ============================================================================

class RegisterRequest(BaseModel):
    """
    Request model for user registration.
    
    Attributes:
        email: User email address (must be unique)
        password: User password (minimum 8 characters)
        name: User full name
        role: User role (default: PM)
    """
    model_config = ConfigDict(str_strip_whitespace=True)
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 chars)")
    name: str = Field(..., max_length=100, description="User full name")
    role: UserRole = Field(default=UserRole.PM, description="User role")
    
    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """
        Validate password strength.
        
        Args:
            v: Password string to validate
            
        Returns:
            Validated password string
            
        Raises:
            ValueError: If password is too weak
        """
        if len(v) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one digit')
        return v


class LoginRequest(BaseModel):
    """
    Request model for user login.
    
    Attributes:
        email: User email address
        password: User password
    """
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class UpdateUserRequest(BaseModel):
    """
    Request model for updating user profile.
    
    Attributes:
        name: New user full name (optional)
        email: New email address (optional)
    """
    name: Optional[str] = Field(None, max_length=100, description="User full name")
    email: Optional[EmailStr] = Field(None, description="New email address")


class CreateProjectRequest(BaseModel):
    """
    Request model for creating a new project.
    
    Attributes:
        name: Project name (required)
        description: Project description (optional)
        start_date: Project start date (optional)
        end_date: Project end date (optional)
        team_member_ids: List of user IDs to add as team members (optional)
    """
    name: str = Field(..., max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=5000, description="Project description")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    team_member_ids: Optional[List[str]] = Field(default_factory=list, description="Team member IDs")
    
    @field_validator('end_date')
    @classmethod
    def validate_end_date(cls, v: Optional[date], info) -> Optional[date]:
        """
        Validate end date is not before start date.
        
        Args:
            v: End date value
            info: Field validation info
            
        Returns:
            Validated end date
            
        Raises:
            ValueError: If end date is before start date
        """
        if v and info.data.get('start_date') and v < info.data['start_date']:
            raise ValueError('End date must be on or after start date')
        return v


class UpdateProjectRequest(BaseModel):
    """
    Request model for updating a project.
    
    Attributes:
        name: Project name (optional)
        description: Project description (optional)
        status: Project status (optional)
        start_date: Project start date (optional)
        end_date: Project end date (optional)
        team_member_ids: List of user IDs to add as team members (optional)
    """
    name: Optional[str] = Field(None, max_length=200, description="Project name")
    description: Optional[str] = Field(None, max_length=5000, description="Project description")
    status: Optional[ProjectStatus] = Field(None, description="Project status")
    start_date: Optional[date] = Field(None, description="Project start date")
    end_date: Optional[date] = Field(None, description="Project end date")
    team_member_ids: Optional[List[str]] = Field(default_factory=list, description="Team member IDs")


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class UserResponse(BaseModel):
    """
    Response model for user information.
    
    Attributes:
        id: User unique identifier
        email: User email address
        name: User full name
        role: User role
        is_active: Whether user account is active
        is_email_verified: Whether email is verified
        created_at: Account creation timestamp
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    email: str
    name: str
    role: UserRole
    is_active: bool = True
    is_email_verified: bool = False
    created_at: datetime


class LoginResponse(BaseModel):
    """
    Response model for login response.
    
    Attributes:
        access_token: JWT access token
        token_type: Token type (bearer)
        expires_in: Token expiration time in seconds
        user: User information
    """
    access_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserResponse


class TeamMember(BaseModel):
    """
    Response model for team member information.
    
    Attributes:
        user_id: User unique identifier
        name: User full name
        email: User email address
        joined_at: When user joined the project
    """
    model_config = ConfigDict(from_attributes=True)
    
    user_id: str
    name: str
    email: str
    joined_at: datetime


class ProjectResponse(BaseModel):
    """
    Response model for project information.
    
    Attributes:
        id: Project unique identifier
        name: Project name
        description: Project description
        status: Project status
        start_date: Project start date
        end_date: Project end date
        owner_id: Owner user ID
        owner: Project owner information
        team_members: List of team members
        created_at: Project creation timestamp
        updated_at: Project last update timestamp
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: str
    name: str
    description: Optional[str] = None
    status: ProjectStatus
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    owner_id: str
    owner: Optional[UserResponse] = None
    team_members: List[TeamMember] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ProjectListResponse(BaseModel):
    """
    Response model for paginated project list.
    
    Attributes:
        total: Total number of projects
        page: Current page number
        page_size: Items per page
        total_pages: Total number of pages
        items: List of project responses
    """
    total: int
    page: int = 1
    page_size: int = 20
    total_pages: int
    items: List[ProjectResponse]


class GanttTask(BaseModel):
    """
    Response model for Gantt chart task.
    
    Attributes:
        id: Task unique identifier
        name: Task name
        start_date: Task start date
        end_date: Task end date
        status: Task status
        progress: Task progress percentage (0-100)
        dependencies: Parent task IDs
        children: Subtasks
    """
    id: str
    name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    status: TaskStatus
    progress: int = Field(ge=0, le=100, default=0)
    dependencies: List[str] = Field(default_factory=list)
    children: List["GanttTask"] = Field(default_factory=list)


class GanttMilestone(BaseModel):
    """
    Response model for Gantt chart milestone.
    
    Attributes:
        id: Milestone unique identifier
        name: Milestone name
        date: Milestone date
    """
    id: str
    name: str
    date: date


class GanttDataResponse(BaseModel):
    """
    Response model for Gantt chart data.
    
    Attributes:
        project_id: Project unique identifier
        project_name: Project name
        start_date: Project start date
        end_date: Project end date
        tasks: List of Gantt tasks
        milestones: List of milestones
    """
    project_id: str
    project_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    tasks: List[GanttTask] = Field(default_factory=list)
    milestones: List[GanttMilestone] = Field(default_factory=list)


class TimelineEvent(BaseModel):
    """
    Response model for timeline event.
    
    Attributes:
        id: Event unique identifier
        event_type: Type of event
        title: Event title
        description: Event description
        event_date: Event date/time
        related_id: Related task/project ID
        related_type: Related entity type
    """
    id: str
    event_type: EventType
    title: str
    description: Optional[str] = None
    event_date: datetime
    related_id: Optional[str] = None
    related_type: Optional[str] = None


class TimelineDataResponse(BaseModel):
    """
    Response model for timeline data.
    
    Attributes:
        project_id: Project unique identifier
        project_name: Project name
        start_date: Filter start date
        end_date: Filter end date
        events: List of timeline events
    """
    project_id: str
    project_name: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    events: List[TimelineEvent] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """
    Response model for error responses.
    
    Attributes:
        error: Error code
        message: Human-readable error message
        details: Additional error details
    """
    error: str
    message: str
    details: Optional[Dict[str, Any]] = None


class HealthResponse(BaseModel):
    """
    Response model for health check endpoint.
    
    Attributes:
        status: Service status
        version: API version
        timestamp: Current timestamp
    """
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
