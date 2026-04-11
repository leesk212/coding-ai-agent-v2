# Project Management System (PMS) - Architectural Design Document

## Version: 1.0
## Date: 2024
## Author: System Architect

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Technology Stack](#3-technology-stack)
4. [Database Schema Design](#4-database-schema-design)
5. [API Architecture](#5-api-architecture)
6. [Frontend/Backend Separation Strategy](#6-frontendbackend-separation-strategy)
7. [Security and Authentication](#7-security-and-authentication)
8. [Gantt Chart Implementation](#8-gantt-chart-implementation)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Technical Trade-offs](#10-technical-trade-offs)

---

## 1. Executive Summary

### 1.1 System Overview
This document outlines the architectural design for a Project Management System (PMS) designed to manage projects, schedules, and team collaboration. The system supports PMs for project creation and Admin/PMO for oversight, with web and mobile access capabilities.

### 1.2 Key Requirements
- **User Roles**: PM, Admin/PMO, Designer, Developer
- **Core Features**: Project management, scheduling, Gantt charts
- **Platforms**: Web (responsive), Mobile (iOS/Android)
- **UX Priority**: User-friendly interface

### 1.3 Design Principles
1. **Modularity**: Loose coupling between modules
2. **Scalability**: Horizontal scaling capability
3. **Security**: RBAC-based access control
4. **Performance**: Optimized for real-time Gantt interactions
5. **Maintainability**: Clean architecture patterns

---

## 2. System Architecture Overview

### 2.1 High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                        │
├──────────────────────┬──────────────────────────┬───────────────────────────────┤
│   Web Application    │  iOS Mobile App          │    Android Mobile App         │
│   (React + TS)       │  (SwiftUI / React Native)│   (Kotlin / React Native)     │
└──────────┬───────────┴──────────┬───────────────┴───────────────┬───────────────┘
           │                      │                               │
           └──────────────────────┼───────────────────────────────┘
                                  │
                          ┌──────▼──────┐
                          │   Load      │
                          │   Balancer  │
                          │  (Nginx)    │
                          └──────┬──────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────────┐
│                           API GATEWAY LAYER                                      │
├─────────────────────────────────────────────────────────────────────────────────┤
│  • Rate Limiting   • Authentication (JWT)   • Request Routing   • SSL Termination│
│  • API Versioning  • Request Logging        • Caching Layer                  │
└─────────────────────────────────────────────────────────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────────┐
│                         MICROSERVICES LAYER                                      │
├──────────────┬──────────────┬──────────────┬──────────────┬─────────────────────┤
│   Auth       │   Project    │   Schedule   │   User       │     Gantt           │
│   Service    │   Service    │   Service    │   Service    │     Service         │
├──────────────┼──────────────┼──────────────┼──────────────┼─────────────────────┤
│ • JWT Mgmt   │ • Project CRUD│ • Task CRUD │ • User CRUD  │ • Timeline Calc     │
│ • RBAC       │ • Client Mgmt │ • Date Calc │ • Role Mgmt  │ • Dependency Mgmt   │
│ • OAuth2     │ • Member Mgmt │ • Alarms    │ • Team Mgmt  │ • Rendering API     │
└──────┬───────┴──────┬───────┴──────┬───────┴──────┬───────┴──────────┬──────────┘
       │              │              │              │                   │
       └──────────────┴──────────────┴──────────────┴───────────────────┘
                                  │
                          ┌──────▼──────┐
                          │   Message   │
                          │   Broker    │
                          │ (RabbitMQ)  │
                          └──────┬──────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────────┐
│                           DATA LAYER                                             │
├──────────────────────┬──────────────────────────┬───────────────────────────────┤
│   PostgreSQL         │   MongoDB                │     Redis                     │
│   (Primary Data)     │   (Documents/Logs)       │     (Cache/Sessions)          │
├──────────────────────┼──────────────────────────┼───────────────────────────────┤
│ • Users              │ • Project Configs        │   • Session Store             │
│ • Projects           │ • Activity Logs          │   • Rate Limit                │
│ • Tasks              │ • Notifications          │   • API Response Cache        │
│ • Schedules          │ • User Preferences       │   • Gantt Cached Data         │
└──────────────────────┴──────────────────────────┴───────────────────────────────┘
                                 │
┌────────────────────────────────▼─────────────────────────────────────────────────┐
│                         EXTERNAL SERVICES                                       │
├──────────────────────┬──────────────────────────┬───────────────────────────────┤
│  Email Service       │  Notification Service    │   File Storage                │
│  (SendGrid/AWS SES)  │  (Firebase/OneSignal)    │   (AWS S3 / Cloudinary)       │
└──────────────────────┴──────────────────────────┴───────────────────────────────┘
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Client Apps** | UI rendering, user interactions, offline caching |
| **Load Balancer** | Traffic distribution, health checks, SSL termination |
| **API Gateway** | Request routing, auth validation, rate limiting |
| **Auth Service** | User authentication, token management, RBAC |
| **Project Service** | Project lifecycle, client management, team assignment |
| **Schedule Service** | Task scheduling, dependency management, timeline calculation |
| **Gantt Service** | Gantt data processing, rendering optimization, export |
| **User Service** | User profile, preferences, notification settings |
| **PostgreSQL** | Relational data storage, ACID transactions |
| **MongoDB** | Document storage, logs, flexible schemas |
| **Redis** | Caching, session management, real-time features |

---

## 3. Technology Stack

### 3.1 Backend Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Language** | Python 3.11+ | Type hints, rich ecosystem, async support |
| **Framework** | FastAPI | High performance, auto docs, async native |
| **ORM** | SQLAlchemy 2.0 + Alembic | Type-safe, migrations, async support |
| **Validation** | Pydantic v2 | Data validation, serialization |
| **Async Task** | Celery + Redis | Background jobs, task queues |
| **Validation** | Pytest | Comprehensive testing framework |
| **Logging** |structlog + ELK | Structured logging, centralized logging |
| **API Docs** | OpenAPI/Swagger | Auto-generated, interactive docs |

### 3.2 Frontend Stack

| Platform | Technology | Rationale |
|----------|-----------|-----------|
| **Web** | React 18 + TypeScript | Component-based, strong typing |
| **State** | Redux Toolkit / Zustand | Predictable state management |
| **Styling** | Tailwind CSS | Utility-first, rapid development |
| **Gantt** | Syncfusion React Gantt / DHTMLX | Feature-rich, customizable |
| **HTTP** | Axios + React Query | Data fetching, caching, sync |
| **Mobile** | React Native | Cross-platform, shared logic |
| **Mobile UI** | React Native Reanimated | Smooth animations |

### 3.3 Infrastructure Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Container** | Docker | Containerization, consistency |
| **Orchestration** | Kubernetes | Scalability, self-healing |
| **Cloud** | AWS / Azure | Enterprise-grade, global reach |
| **CI/CD** | GitHub Actions | Automation, integration |
| **Monitoring** | Prometheus + Grafana | Metrics, alerting |
| **Tracing** | Jaeger | Distributed tracing |
| **Database** | PostgreSQL 15 | ACID, JSON support, extensions |
| **Cache** | Redis 7 | In-memory, pub/sub, streams |
| **Message** | RabbitMQ | Reliable messaging, routing |
| **Storage** | AWS S3 | File storage, CDN integration |

### 3.3.1 Technology Stack Summary

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TECHNOLOGY STACK                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  CLIENT SIDE                                                         │
│  ┌──────────────┬───────────────────────────────────────────────┐   │
│  │ Web (Desktop)│ React 18 + TypeScript, Tailwind CSS           │   │
│  │              │ Syncfusion Gantt Component, Redux Toolkit     │   │
│  ├──────────────┼───────────────────────────────────────────────┤   │
│  │ Mobile iOS   │ React Native, React Native Reanimated         │   │
│  │ Mobile Android│ React Native, Native Modules                 │   │
│  └──────────────┴───────────────────────────────────────────────┘   │
│                                                                      │
│  BACKEND SIDE                                                        │
│  ┌──────────────┬───────────────────────────────────────────────┐   │
│  │ Framework    │ FastAPI (Python 3.11+)                        │   │
│  │ ORM          │ SQLAlchemy 2.0 + Alembic (Migrations)         │   │
│  │ Validation   │ Pydantic v2                                   │   │
│  │ Background   │ Celery + Redis (Task Queue)                   │   │
│  │ Testing      │ Pytest + pytest-asyncio                       │   │
│  └──────────────┴───────────────────────────────────────────────┘   │
│                                                                      │
│  DATABASE LAYER                                                      │
│  ┌──────────────┬───────────────────────────────────────────────┐   │
│  │ Primary DB   │ PostgreSQL 15 (JSONB, Extensions)             │   │
│  │ Cache        │ Redis 7 (Session, Cache, Rate Limit)          │   │
│  │ Document DB  │ MongoDB (Logs, Config, Activity)              │   │
│  └──────────────┴───────────────────────────────────────────────┘   │
│                                                                      │
│  INFRASTRUCTURE                                                      │
│  ┌──────────────┬───────────────────────────────────────────────┐   │
│  │ Container    │ Docker + Docker Compose (Dev)                 │   │
│  │ Orchestration│ Kubernetes (Prod)                             │   │
│  │ Cloud        │ AWS (EKS, RDS, S3, CloudFront)                │   │
│  │ CI/CD        │ GitHub Actions                                │   │
│  │ Monitoring   │ Prometheus + Grafana + ELK Stack              │   │
│  └──────────────┴───────────────────────────────────────────────┘   │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. Database Schema Design

### 4.1 Entity Relationship Diagram

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│     USER        │       │    ROLE         │       │   PERMISSION    │
├─────────────────┤       ├─────────────────┤       ├─────────────────┤
│ id (PK)         │◄──────│ id (PK)         │       │ id (PK)         │
│ email           │   1   │ name            │   N   │ name            │
│ password_hash   │       │ description     │       │ description     │
│ first_name      │       └────────┬────────┘       └────────┬────────┘
│ last_name       │                │                        │
│ avatar_url      │                │ 1                      │ N
│ role_id (FK)    │────────────────┼────────────────────────┼──────┐
│ status          │                │                        │      │
│ created_at      │                │ N                      │      ▼
│ updated_at      │                ▼                        ┌─────────────────┐
└────────┬────────┘       ┌─────────────────┐               │    USER_ROLE    │
         │               │    USER_ROLE    │               ├─────────────────┤
         │ N             │ id (PK)         │               │ id (PK)         │
         │               │ user_id (FK)    │◄──────────────│ user_id (FK)      │
         │               │ role_id (FK)    │               │ role_id (FK)      │
         │               │ project_id (FK) │               │ project_id (FK)   │
         │               │ permissions     │               │ permissions       │
         │               │ created_at      │               │ created_at        │
         └──────────────►│ updated_at      │               └─────────────────┘
                        └────────┬────────┘
                                 │ N
                                 │
                        ┌────────▼────────┐
                        │    CLIENT       │
                        ├─────────────────┤
                        │ id (PK)         │
                        │ name            │
                        │ contact_person  │
                        │ email           │
                        │ phone           │
                        │ address         │
                        │ created_at      │
                        │ updated_at      │
                        └────────┬────────┘
                                 │ N
                                 │
                        ┌────────▼────────┐
                        │   PROJECT       │
                        ├─────────────────┤
                        │ id (PK)         │
                        │ code            │
                        │ name            │
                        │ client_id (FK)  │◄──────┐
                        │ description     │       │
                        │ start_date      │       │
                        │ end_date        │       │
                        │ status          │       │
                        │ priority        │       │
                        │ budget          │       │
                        │ manager_id (FK) │───────┘
                        │ created_at      │
                        │ updated_at      │
                        └────────┬────────┘
                                 │ N
                                 │
                        ┌────────▼────────┐
                        │     TASK        │
                        ├─────────────────┤
                        │ id (PK)         │
                        │ project_id (FK) │──────────┐
                        │ name            │          │
                        │ description     │          │
                        │ assignee_id(FK) │          │
                        │ parent_task_id  │◄─────────┘
                        │ (FK, self-ref)  │    N     │ 1
                        │ status          │          │
                        │ priority        │    N     │
                        │ start_date      │──────────┼──────┐
                        │ due_date        │          │      │
                        │ estimated_hours │          │      │
                        │ actual_hours    │          │      │
                        │ order_index     │          │      │
                        │ created_at      │          │      │
                        │ updated_at      │          │      │
                        └────────┬────────┘          │      │
                                 │                   │      │
                        ┌────────▼────────┐          │      │
                        │  TASK_DEPENDENCY│          │      │
                        ├─────────────────┤          │      │
                        │ id (PK)         │          │      │
                        │ task_id (FK)    │──────────┘      │
                        │ depends_on_id │                   │
                        │ (FK, task.id) │                   │
                        │ dependency_type│                   │
                        │ (FS, FF, SF, SS)│                  │
                        └─────────────────┘                   │
                                                            │
                        ┌─────────────────┐                  │
                        │   SCHEDULE_DATE │◄─────────────────┘
                        ├─────────────────┤
                        │ id (PK)         │
                        │ project_id(FK)  │
                        │ task_id (FK)    │
                        │ date            │
                        │ is_working_day  │
                        │ is_holiday      │
                        │ created_at      │
                        └─────────────────┘
```

### 4.2 Database Schema (SQLAlchemy Models)

```python
"""
PMS Database Schema Models

This module defines the core database models for the Project Management System.
All models use SQLAlchemy 2.0 with async support.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, TYPE_CHECKING

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean,
    Float, Enum as SQLEnum, Table, UniqueConstraint, Index
)
from sqlalchemy.orm import relationship, declarative_base, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID

Base = declarative_base()

# Association tables
user_role_association = Table(
    'user_role',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('role_id', Integer, ForeignKey('roles.id'), primary_key=True),
    Column('project_id', Integer, ForeignKey('projects.id'), nullable=True),
    Column('permissions', JSONB, default=list),
    Column('created_at', DateTime, default=datetime.utcnow)
)

task_dependency = Table(
    'task_dependency',
    Base.metadata,
    Column('id', Integer, primary_key=True),
    Column('task_id', Integer, ForeignKey('tasks.id'), index=True),
    Column('depends_on_id', Integer, ForeignKey('tasks.id'), index=True),
    Column('dependency_type', String(2), default='FS'),  # FS, FF, SF, SS
    Index('idx_task_deps', 'task_id', 'depends_on_id', unique=True)
)


class UserStatus(Enum):
    ACTIVE = 'active'
    INACTIVE = 'inactive'
    ON_LEAVE = 'on_leave'
    RESIGNED = 'resigned'


class TaskStatus(Enum):
    TODO = 'todo'
    IN_PROGRESS = 'in_progress'
    BLOCKED = 'blocked'
    COMPLETED = 'completed'
    ARCHIVED = 'archived'


class TaskPriority(Enum):
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    CRITICAL = 'critical'


class ProjectStatus(Enum):
    PLANNING = 'planning'
    ACTIVE = 'active'
    ON_HOLD = 'on_hold'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class UserRole(Base):
    """
    User Role Assignment Model
    
    Manages user-role assignments with optional project-level scoping
    and custom permissions override.
    """
    __tablename__ = 'user_role'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id'), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey('projects.id'), nullable=True)
    permissions: Mapped[List[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="project_roles")
    role = relationship("Role", back_populates="user_roles")
    project = relationship("Project", back_populates="user_roles")


class User(Base):
    """
    User Model
    
    Core user entity with authentication and profile information.
    Supports multiple roles across projects.
    """
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    status: Mapped[UserStatus] = mapped_column(SQLEnum(UserStatus), default=UserStatus.ACTIVE)
    timezone: Mapped[str] = mapped_column(String(50), default='Asia/Seoul')
    language: Mapped[str] = mapped_column(String(10), default='ko')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime)

    # Relationships
    project_roles: Mapped[List["UserRole"]] = relationship("UserRole", back_populates="user")
    assigned_tasks: Mapped[List["Task"]] = relationship("Task", foreign_keys="Task.assignee_id", back_populates="assignee")
    created_tasks: Mapped[List["Task"]] = relationship("Task", foreign_keys="Task.creator_id", back_populates="creator")
    manager_projects: Mapped[List["Project"]] = relationship("Project", foreign_keys="Project.manager_id", back_populates="manager")


class Role(Base):
    """
    Role Model
    
    Defines system roles with default permissions.
    Roles can be global or project-specific.
    """
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    permissions: Mapped[List[str]] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user_roles: Mapped[List["UserRole"]] = relationship("UserRole", back_populates="role")


class Client(Base):
    """
    Client Model
    
    Manages client organizations and their contact information.
    """
    __tablename__ = 'clients'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    contact_person: Mapped[Optional[str]] = mapped_column(String(100))
    email: Mapped[Optional[str]] = mapped_column(String(255))
    phone: Mapped[Optional[str]] = mapped_column(String(20))
    address: Mapped[Optional[str]] = mapped_column(Text)
    website: Mapped[Optional[str]] = mapped_column(String(200))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="client")


class Project(Base):
    """
    Project Model
    
    Core project entity with schedule, team, and client relationships.
    Supports task hierarchy and dependencies.
    """
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    client_id: Mapped[int] = mapped_column(ForeignKey('clients.id'), index=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_date: Mapped[datetime] = mapped_column(DateTime)
    end_date: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[ProjectStatus] = mapped_column(SQLEnum(ProjectStatus), default=ProjectStatus.PLANNING)
    priority: Mapped[TaskPriority] = mapped_column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    budget: Mapped[Optional[float]] = mapped_column(Float)
    manager_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    color_code: Mapped[Optional[str]] = mapped_column(String(7))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    client: Mapped["Client"] = relationship("Client", back_populates="projects")
    manager: Mapped["User"] = relationship("User", foreign_keys=[manager_id], back_populates="manager_projects")
    user_roles: Mapped[List["UserRole"]] = relationship("UserRole", back_populates="project")
    tasks: Mapped[List["Task"]] = relationship("Task", back_populates="project", cascade="all, delete-orphan")
    schedule_dates: Mapped[List["ScheduleDate"]] = relationship("ScheduleDate", back_populates="project")


class Task(Base):
    """
    Task Model
    
    Task entity with hierarchical structure (parent-child) and dependencies.
    Supports time tracking and status workflow.
    """
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[Optional[str]] = mapped_column(Text)
    assignee_id: Mapped[Optional[int]] = mapped_column(ForeignKey('users.id'), index=True)
    parent_task_id: Mapped[Optional[int]] = mapped_column(ForeignKey('tasks.id'), index=True)
    status: Mapped[TaskStatus] = mapped_column(SQLEnum(TaskStatus), default=TaskStatus.TODO)
    priority: Mapped[TaskPriority] = mapped_column(SQLEnum(TaskPriority), default=TaskPriority.MEDIUM)
    start_date: Mapped[datetime] = mapped_column(DateTime)
    due_date: Mapped[datetime] = mapped_column(DateTime)
    estimated_hours: Mapped[Optional[float]] = mapped_column(Float)
    actual_hours: Mapped[Optional[float]] = mapped_column(Float)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    order_index: Mapped[int] = mapped_column(Integer, default=0)
    wbs_code: Mapped[Optional[str]] = mapped_column(String(50))
    tags: Mapped[Optional[List[str]]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="tasks")
    assignee: Mapped["User"] = relationship("User", foreign_keys=[assignee_id], back_populates="assigned_tasks")
    creator: Mapped["User"] = relationship("User", foreign_keys="Task.creator_id", back_populates="created_tasks")
    parent: Mapped[Optional["Task"]] = relationship("Task", remote_side=[id], back_populates="subtasks")
    subtasks: Mapped[List["Task"]] = relationship("Task", back_populates="parent")
    dependencies: Mapped[List["Task"]] = relationship("Task", secondary=task_dependency,
                                                       primaryjoin="Task.id == task_dependency.c.task_id",
                                                       secondaryjoin="Task.id == task_dependency.c.depends_on_id")


class ScheduleDate(Base):
    """
    Schedule Date Model
    
    Stores working days and holidays for project scheduling.
    Used for accurate timeline calculation in Gantt charts.
    """
    __tablename__ = 'schedule_dates'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey('projects.id'), index=True)
    task_id: Mapped[Optional[int]] = mapped_column(ForeignKey('tasks.id'), index=True)
    date: Mapped[datetime] = mapped_column(DateTime)
    is_working_day: Mapped[bool] = mapped_column(Boolean, default=True)
    is_holiday: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    project: Mapped["Project"] = relationship("Project", back_populates="schedule_dates")
    task: Mapped[Optional["Task"]] = relationship("Task", back_populates="schedule_dates")

    __table_args__ = (
        UniqueConstraint('project_id', 'date', name='ux_project_date'),
        UniqueConstraint('task_id', 'date', name='ux_task_date'),
        Index('idx_schedule_date', 'project_id', 'date')
    )


class ActivityLog(Base):
    """
    Activity Log Model
    
    Tracks all user actions for audit trail and activity feed.
    Stored in MongoDB for high write performance.
    """
    __tablename__ = 'activity_logs'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey('projects.id'), index=True)
    action: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[Optional[int]] = mapped_column(Integer)
    old_value: Mapped[Optional[str]] = mapped_column(JSONB)
    new_value: Mapped[Optional[str]] = mapped_column(JSONB)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index('idx_activity_created', 'created_at'),
        Index('idx_activity_entity', 'entity_type', 'entity_id'),
    )