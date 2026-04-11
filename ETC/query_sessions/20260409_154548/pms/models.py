"""
PMS (Project Management System) - Database Models

Defines SQLAlchemy models for User, Project, and ProjectMember tables.
"""
from datetime import datetime
from typing import List, Optional
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(db.Model):
    """User model for authentication and role management."""
    
    __tablename__ = 'users'
    
    id: int = db.Column(db.Integer, primary_key=True)
    username: str = db.Column(db.String(80), unique=True, nullable=False)
    email: str = db.Column(db.String(120), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(256), nullable=False)
    role: str = db.Column(db.String(20), nullable=False)  # 'admin', 'pm', 'member'
    is_active: bool = db.Column(db.Boolean, default=True)
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    projects_as_pm: List['Project'] = db.relationship('Project', backref='project_manager', lazy='dynamic')
    project_members: List['ProjectMember'] = db.relationship('ProjectMember', backref='user', lazy='dynamic')
    
    def set_password(self, password: str) -> None:
        """Hash and set user password."""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Verify password against hash."""
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self) -> bool:
        """Check if user has admin role."""
        return self.role == 'admin'
    
    @property
    def is_pm(self) -> bool:
        """Check if user has PM role."""
        return self.role == 'pm'
    
    def to_dict(self) -> dict:
        """Convert user to dictionary."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self) -> str:
        return f'<User {self.username}>'


class Project(db.Model):
    """Project model for project management."""
    
    __tablename__ = 'projects'
    
    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(200), nullable=False)
    code: str = db.Column(db.String(50), unique=True, nullable=False)
    client: str = db.Column(db.String(200), nullable=False)
    description: Optional[str] = db.Column(db.Text)
    
    # Schedule
    start_date: datetime = db.Column(db.DateTime, nullable=False)
    end_date: datetime = db.Column(db.DateTime, nullable=False)
    actual_start_date: Optional[datetime] = db.Column(db.DateTime)
    actual_end_date: Optional[datetime] = db.Column(db.DateTime)
    
    status: str = db.Column(db.String(20), default='planning')  # planning, active, completed, on_hold, cancelled
    
    # Timestamps
    created_at: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at: datetime = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Foreign keys
    pm_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    members: List['ProjectMember'] = db.relationship('ProjectMember', backref='project', lazy='dynamic',
                                                       cascade='all, delete-orphan')
    
    def add_member(self, user_id: int, role: str = 'developer') -> 'ProjectMember':
        """Add a member to the project."""
        member = ProjectMember(project_id=self.id, user_id=user_id, role=role)
        db.session.add(member)
        db.session.commit()
        return member
    
    def get_designers(self) -> List['ProjectMember']:
        """Get all designers in the project."""
        return [m for m in self.members if m.role == 'designer']
    
    def get_developers(self) -> List['ProjectMember']:
        """Get all developers in the project."""
        return [m for m in self.members if m.role == 'developer']
    
    def is_overdue(self) -> bool:
        """Check if project is overdue."""
        if self.status in ['completed', 'cancelled']:
            return False
        return datetime.utcnow() > self.end_date
    
    def to_dict(self) -> dict:
        """Convert project to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'client': self.client,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'actual_start_date': self.actual_start_date.isoformat() if self.actual_start_date else None,
            'actual_end_date': self.actual_end_date.isoformat() if self.actual_end_date else None,
            'status': self.status,
            'is_overdue': self.is_overdue(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self) -> str:
        return f'<Project {self.code}: {self.name}>'


class ProjectMember(db.Model):
    """Project member relationship model."""
    
    __tablename__ = 'project_members'
    
    id: int = db.Column(db.Integer, primary_key=True)
    project_id: int = db.Column(db.Integer, db.ForeignKey('projects.id'), nullable=False)
    user_id: int = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    role: str = db.Column(db.String(20), nullable=False)  # designer, developer, lead
    assigned_date: datetime = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self) -> dict:
        """Convert project member to dictionary."""
        return {
            'id': self.id,
            'project_id': self.project_id,
            'user_id': self.user_id,
            'role': self.role,
            'assigned_date': self.assigned_date.isoformat() if self.assigned_date else None,
            'user': self.user.to_dict() if self.user else None
        }
    
    def __repr__(self) -> str:
        return f'<ProjectMember {self.user.username} in {self.project.code}>'
