"""
SQLAlchemy database models for Project Management System.

This module defines the database schema following SQLAlchemy ORM patterns.
Models correspond to the Pydantic schemas and support the business logic requirements.
"""

from datetime import datetime, date
from typing import Optional, List, Set
from enum import Enum
from uuid import uuid4
import uuid

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    DateTime,
    Date,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    PrimaryKeyConstraint,
    Index,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declared_attr, Mapped, mapped_column
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.exc import IntegrityError

# Import base model class
Base = declarative_base()


# ============================================================================
# ENUM CLASSES
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


# ============================================================================
# BASE MODEL CLASS
# ============================================================================

class BaseModel(Base):
    """
    Base model with common fields for all tables.
    
    Attributes:
        id: Unique identifier (UUID)
        created_at: Creation timestamp
        updated_at: Last update timestamp
        is_deleted: Soft delete flag
    """
    
    __abstract__ = True
    
    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4())
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    
    is_deleted: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True
    )
    
    __table_args__ = (
        Index('idx_created_at', 'created_at'),
        Index('idx_updated_at', 'updated_at'),
    )
    
    def to_dict(self) -> dict:
        """Convert model to dictionary representation."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_deleted': self.is_deleted,
        }


# ============================================================================
# USER MODEL
# ============================================================================

class User(BaseModel):
    """
    User model representing system users.
    
    Users can be PMs (Project Managers) or Admins.
    Users own projects and can be team members on other projects.
    
    Attributes:
        email: Unique email address (login credential)
        password_hash: BCrypt hashed password
        name: User's full name
        role: User role (PM or ADMIN)
        is_active: Whether user account is active
        is_email_verified: Whether email is verified
        email_verified_at: Email verification timestamp
    """
    
    __tablename__ = "users"
    
    # Identity fields
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True
    )
    
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    
    role: Mapped[str] = mapped_column(
        SQLEnum(UserRole),
        default=UserRole.PM,
        nullable=False
    )
    
    # Account status
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    
    email_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True
    )
    
    # Relationships
    owned_projects: Mapped[List["Project"]] = relationship(
        "Project",
        back_populates="owner",
        foreign_keys="Project.owner_id",
        lazy="dynamic"
    )
    
    team_memberships: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        CheckConstraint(
            "role IN ('PM', 'ADMIN')",
            name="check_valid_user_role"
        ),
    )
    
    @hybrid_property
    def email_lower(self) -> str:
        """Lowercase email for case-insensitive lookups."""
        return self.email.lower()
    
    @email_lower.expression
    @classmethod
    def email_lower(cls):
        """SQL expression for lowercase email."""
        return func.lower(cls.email)
    
    def set_password(self, password: str, password_hasher: callable) -> None:
        """
        Set or update user password.
        
        Args:
            password: Plain text password
            password_hasher: Function to hash the password
        """
        self.password_hash = password_hasher(password)
    
    def check_password(self, password: str, password_verifier: callable) -> bool:
        """
        Verify password against stored hash.
        
        Args:
            password: Plain text password to verify
            password_verifier: Function to verify password hash
            
        Returns:
            True if password matches, False otherwise
        """
        return password_verifier(password, self.password_hash)
    
    def verify_email(self) -> None:
        """Mark user email as verified."""
        self.is_email_verified = True
        self.email_verified_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Convert user to dictionary (excludes sensitive data)."""
        result = super().to_dict()
        result.update({
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'is_active': self.is_active,
            'is_email_verified': self.is_email_verified,
        })
        return result


# ============================================================================
# PROJECT MODEL
# ============================================================================

class Project(BaseModel):
    """
    Project model representing a work project.
    
    Projects have an owner (who creates the project) and can have
    multiple team members.
    
    Attributes:
        name: Project name
        description: Project description
        status: Current project status
        start_date: Project start date
        end_date: Project end date
        owner_id: Reference to user who owns the project
    """
    
    __tablename__ = "projects"
    
    # Basic info
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    status: Mapped[str] = mapped_column(
        SQLEnum(ProjectStatus),
        default=ProjectStatus.PLANNING,
        nullable=False
    )
    
    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )
    
    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )
    
    # Foreign key to owner
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    # Relationships
    owner: Mapped["User"] = relationship(
        "User",
        back_populates="owned_projects",
        foreign_keys=[owner_id]
    )
    
    team_members: Mapped[List["TeamMember"]] = relationship(
        "TeamMember",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    tasks: Mapped[List["Task"]] = relationship(
        "Task",
        back_populates="project",
        cascade="all, delete-orphan"
    )
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('planning', 'in_progress', 'on_hold', 'completed', 'cancelled')",
            name="check_valid_project_status"
        ),
        CheckConstraint(
            "name IS NOT NULL AND LENGTH(name) > 0",
            name="check_project_name_not_empty"
        ),
        Index('idx_project_owner', 'owner_id', 'is_deleted'),
    )
    
    @property
    def team_member_ids(self) -> List[str]:
        """Get list of all team member user IDs."""
        return [tm.user_id for tm in self.team_members]
    
    @property
    def is_owner(self, current_user_id: str) -> bool:
        """Check if current user is the project owner."""
        return self.owner_id == current_user_id
    
    def add_team_member(self, user_id: str) -> "TeamMember":
        """
        Add a team member to the project.
        
        Args:
            user_id: User ID to add as team member
            
        Returns:
            Created TeamMember object
        """
        team_member = TeamMember(project_id=self.id, user_id=user_id)
        self.team_members.append(team_member)
        return team_member
    
    def remove_team_member(self, user_id: str) -> bool:
        """
        Remove a team member from the project.
        
        Args:
            user_id: User ID to remove
            
        Returns:
            True if removed, False if not found
        """
        for tm in self.team_members:
            if tm.user_id == user_id:
                self.team_members.remove(tm)
                return True
        return False
    
    def can_transition_to_status(self, new_status: str) -> bool:
        """
        Check if project can transition to new status.
        
        Args:
            new_status: Target status
            
        Returns:
            True if transition is valid
        """
        valid_transitions = {
            'planning': ['in_progress', 'cancelled', 'on_hold'],
            'in_progress': ['on_hold', 'completed', 'cancelled'],
            'on_hold': ['in_progress', 'cancelled', 'completed'],
            'completed': [],
            'cancelled': [],
        }
        
        current_statuses = valid_transitions.get(self.status, [])
        return new_status in current_statuses
    
    def to_dict(self) -> dict:
        """Convert project to dictionary."""
        result = super().to_dict()
        result.update({
            'name': self.name,
            'description': self.description,
            'status': self.status,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'owner_id': self.owner_id,
        })
        return result


# ============================================================================
# TEAM MEMBER MODEL (Association Table)
# ============================================================================

class TeamMember(BaseModel):
    """
    Team member association model linking users to projects.
    
    This junction table allows users to be members of multiple projects
    and projects to have multiple members.
    
    Attributes:
        project_id: Reference to project
        user_id: Reference to user
        joined_at: When user joined the project
    """
    
    __tablename__ = "team_members"
    
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True
    )
    
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id"),
        nullable=False,
        index=True
    )
    
    joined_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
        nullable=False
    )
    
    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="team_members"
    )
    
    user: Mapped["User"] = relationship(
        "User",
        back_populates="team_memberships"
    )
    
    __table_args__ = (
        PrimaryKeyConstraint("project_id", "user_id"),
        Index('idx_team_user', 'user_id', 'is_deleted'),
    )


# ============================================================================
# TASK MODEL
# ============================================================================

class Task(BaseModel):
    """
    Task model representing work items within a project.
    
    Tasks are used to break down project work into manageable units.
    They can have parent-child relationships for task breakdowns.
    
    Attributes:
        name: Task name
        description: Task description
        status: Current task status
        start_date: Task start date
        end_date: Task end date
        project_id: Reference to project
        parent_id: Reference to parent task (optional)
    """
    
    __tablename__ = "tasks"
    
    # Basic info
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )
    
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    
    status: Mapped[str] = mapped_column(
        SQLEnum(TaskStatus),
        default=TaskStatus.TODO,
        nullable=False
    )
    
    start_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )
    
    end_date: Mapped[Optional[date]] = mapped_column(
        Date,
        nullable=True
    )
    
    # Relationships
    project_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("projects.id"),
        nullable=False,
        index=True
    )
    
    parent_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("tasks.id"),
        nullable=True,
        index=True
    )
    
    # Relationships
    project: Mapped["Project"] = relationship(
        "Project",
        back_populates="tasks"
    )
    
    parent: Mapped[Optional["Task"]] = relationship(
        "Task",
        remote_side="Task.id",
        backref="subtasks"
    )
    
    __table_args__ = (
        CheckConstraint(
            "status IN ('todo', 'in_progress', 'blocked', 'completed', 'cancelled')",
            name="check_valid_task_status"
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="check_task_dates_valid"
        ),
    )
    
    def can_transition_to_status(self, new_status: str) -> bool:
        """
        Check if task can transition to new status.
        
        Args:
            new_status: Target status
            
        Returns:
            True if transition is valid
        """
        valid_transitions = {
            'todo': ['in_progress', 'blocked', 'cancelled'],
            'in_progress': ['completed', 'blocked', 'cancelled'],
            'blocked': ['in_progress', 'cancelled'],
            'completed': ['cancelled'],
            'cancelled': [],
        }
        
        current_statuses = valid_transitions.get(self.status, [])
        return new_status in current_statuses
    
    def calculate_duration(self) -> Optional[int]:
        """
        Calculate task duration in days.
        
        Returns:
            Duration in days, or None if dates not set
        """
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days
        return None


# ============================================================================
# DATABASE SESSION MANAGEMENT
# ============================================================================

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


class DatabaseManager:
    """
    Database manager for session handling.
    
    Provides centralized database connection and session management.
    """
    
    def __init__(self, database_url: str):
        """
        Initialize database manager.
        
        Args:
            database_url: Database connection URL
        """
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
    
    def get_session(self) -> Session:
        """
        Get a new database session.
        
        Returns:
            SQLAlchemy session
        """
        return self.SessionLocal()
    
    def create_all(self) -> None:
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
    
    def drop_all(self) -> None:
        """Drop all database tables."""
        Base.metadata.drop_all(bind=self.engine)
    
    def get_or_create(
        self,
        model,
        defaults=None,
        **kwargs
    ) -> tuple:
        """
        Get or create a model instance.
        
        Args:
            model: Model class
            defaults: Default values for creation
            **kwargs: Query fields
            
        Returns:
            Tuple of (instance, created)
        """
        session = self.get_session()
        try:
            instance = session.query(model).filter_by(**kwargs).first()
            
            if instance:
                return (instance, False)
            
            create_kwargs = {**kwargs, **(defaults or {})}
            instance = model(**create_kwargs)
            session.add(instance)
            session.commit()
            session.refresh(instance)
            
            return (instance, True)
        except IntegrityError:
            session.rollback()
            instance = session.query(model).filter_by(**kwargs).first()
            return (instance, False)
        finally:
            session.close()


# ============================================================================
# EXPORTS
# ============================================================================

__all__ = [
    # Enums
    'UserRole',
    'ProjectStatus',
    'TaskStatus',
    
    # Base model
    'Base',
    'BaseModel',
    
    # Models
    'User',
    'Project',
    'TeamMember',
    'Task',
    
    # Database manager
    'DatabaseManager',
]
