"""
Business Logic Specifications for Project Management System.

This module defines all business rules, validation logic, and domain specifications
for the PMS backend following Spec Driven Development principles.
"""

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional, List, Set, Dict, Any
from enum import Enum
from pydantic import BaseModel


# ============================================================================
# BUSINESS RULES AND CONSTANTS
# ============================================================================

class BusinessRule:
    """
    Container for all business rules and constants.
    
    This class centralizes all business logic constants and rules
    for easy maintenance and testing.
    """
    
    # Token Configuration
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # Password Requirements
    MIN_PASSWORD_LENGTH: int = 8
    PASSWORD_MIN_UPPERCASE: int = 1
    PASSWORD_MIN_DIGIT: int = 1
    
    # Pagination Defaults
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100
    MIN_PAGE_SIZE: int = 1
    
    # Date Validation
    MAX_PROJECT_DURATION_DAYS: int = 3650  # 10 years
    MIN_DATE_FUTURE: int = 365 * 10  # 10 years in future
    
    # Rate Limiting
    LOGIN_ATTEMPTS_LIMIT: int = 5
    LOGIN_ATTEMPTS_WINDOW_SECONDS: int = 300  # 5 minutes
    
    # Project Status Transitions
    VALID_STATUS_TRANSITIONS: Dict[str, Set[str]] = {
        'planning': {'in_progress', 'cancelled'},
        'in_progress': {'on_hold', 'completed', 'cancelled'},
        'on_hold': {'in_progress', 'completed', 'cancelled'},
        'completed': set(),  # Terminal state
        'cancelled': set(),  # Terminal state
    }
    
    # Task Status Transitions
    VALID_TASK_TRANSITIONS: Dict[str, Set[str]] = {
        'todo': {'in_progress', 'cancelled'},
        'in_progress': {'blocked', 'completed', 'cancelled'},
        'blocked': {'in_progress', 'cancelled'},
        'completed': set(),  # Terminal state
        'cancelled': set(),  # Terminal state
    }


class PermissionLevel(Enum):
    """
    Enumeration of permission levels for authorization.
    """
    PUBLIC = "public"
    AUTHENTICATED = "authenticated"
    PM = "pm"
    ADMIN = "admin"


class UserContext(BaseModel):
    """
    Context object containing authenticated user information.
    
    Attributes:
        id: User unique identifier
        email: User email address
        name: User full name
        role: User role (PM or ADMIN)
        is_active: Whether user account is active
    """
    id: str
    email: str
    name: str
    role: str
    is_active: bool


class ProjectContext(BaseModel):
    """
    Context object containing project and permission information.
    
    Attributes:
        project_id: Project unique identifier
        is_owner: Whether the user is the project owner
        is_admin: Whether the user has admin privileges
        is_team_member: Whether the user is a team member
        can_edit: Whether the user can edit the project
        can_delete: Whether the user can delete the project
    """
    project_id: str
    is_owner: bool = False
    is_admin: bool = False
    is_team_member: bool = False
    can_edit: bool = False
    can_delete: bool = False


class OperationResult(BaseModel):
    """
    Generic operation result wrapper.
    
    Attributes:
        success: Whether the operation succeeded
        data: Operation result data (if successful)
        error: Error message (if failed)
        details: Additional error details
    """
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    
    @classmethod
    def success_result(cls, data: Any) -> "OperationResult":
        """Create a successful operation result."""
        return cls(success=True, data=data)
    
    @classmethod
    def error_result(cls, error: str, details: Optional[Dict[str, Any]] = None) -> "OperationResult":
        """Create a failed operation result."""
        return cls(success=False, error=error, details=details)


# ============================================================================
# AUTHORIZATION LOGIC
# ============================================================================

class AuthorizationLogic:
    """
    Authorization logic for determining user permissions.
    
    This class contains all authorization rules and permission checking logic.
    """
    
    @staticmethod
    def determine_permissions(
        user: UserContext,
        project_owner_id: Optional[str],
        team_member_ids: Optional[List[str]]
    ) -> ProjectContext:
        """
        Determine user permissions for a project.
        
        Args:
            user: Authenticated user context
            project_owner_id: ID of project owner
            team_member_ids: List of team member IDs
            
        Returns:
            ProjectContext with computed permissions
        """
        is_owner = project_owner_id == user.id
        is_admin = user.role == "ADMIN"
        team_members = team_member_ids or []
        is_team_member = user.id in team_members
        
        # Admin has all permissions
        if is_admin:
            return ProjectContext(
                project_id=project_owner_id,
                is_owner=is_owner,
                is_admin=True,
                is_team_member=True,
                can_edit=True,
                can_delete=True,
            )
        
        # Owner has edit and delete permissions
        if is_owner:
            return ProjectContext(
                project_id=project_owner_id,
                is_owner=True,
                is_admin=False,
                is_team_member=True,
                can_edit=True,
                can_delete=True,
            )
        
        # Team member can only read
        if is_team_member:
            return ProjectContext(
                project_id=project_owner_id,
                is_owner=False,
                is_admin=False,
                is_team_member=True,
                can_edit=False,
                can_delete=False,
            )
        
        # Not involved
        return ProjectContext(
            project_id=project_owner_id,
            is_owner=False,
            is_admin=False,
            is_team_member=False,
            can_edit=False,
            can_delete=False,
        )
    
    @staticmethod
    def requires_admin(permission_level: PermissionLevel, user: UserContext) -> bool:
        """
        Check if user has required permission level.
        
        Args:
            permission_level: Required permission level
            user: Authenticated user context
            
        Returns:
            True if user has required permission
        """
        if permission_level == PermissionLevel.PUBLIC:
            return True
        elif permission_level == PermissionLevel.AUTHENTICATED:
            return user.is_active
        elif permission_level == PermissionLevel.PM:
            return user.is_active and user.role in ["PM", "ADMIN"]
        elif permission_level == PermissionLevel.ADMIN:
            return user.is_active and user.role == "ADMIN"
        return False


# ============================================================================
# PROJECT STATUS TRANSITIONS
# ============================================================================

class ProjectStatusTransition:
    """
    Business logic for project status transitions.
    """
    
    @staticmethod
    def is_valid_transition(
        current_status: str,
        new_status: str
    ) -> bool:
        """
        Check if status transition is valid.
        
        Args:
            current_status: Current project status
            new_status: Target status
            
        Returns:
            True if transition is allowed
        """
        transitions = BusinessRule.VALID_STATUS_TRANSITIONS
        return new_status in transitions.get(current_status, set())
    
    @staticmethod
    def is_terminal_status(status: str) -> bool:
        """
        Check if status is terminal (cannot transition out).
        
        Args:
            status: Project status to check
            
        Returns:
            True if status is terminal
        """
        return status in ["completed", "cancelled"]


# ============================================================================
# PAGINATION LOGIC
# ============================================================================

class PaginationLogic:
    """
    Business logic for pagination operations.
    """
    
    @staticmethod
    def validate_page_params(
        page: Optional[int] = None,
        page_size: Optional[int] = None
    ) -> tuple:
        """
        Validate and normalize pagination parameters.
        
        Args:
            page: Page number (1-indexed)
            page_size: Items per page
            
        Returns:
            Tuple of (page, page_size)
            
        Raises:
            ValueError: If parameters are invalid
        """
        page = page or 1
        page_size = page_size or BusinessRule.DEFAULT_PAGE_SIZE
        
        if page < 1:
            raise ValueError("Page number must be at least 1")
        
        if page_size < BusinessRule.MIN_PAGE_SIZE:
            raise ValueError(
                f"Page size must be at least {BusinessRule.MIN_PAGE_SIZE}"
            )
        
        if page_size > BusinessRule.MAX_PAGE_SIZE:
            raise ValueError(
                f"Page size cannot exceed {BusinessRule.MAX_PAGE_SIZE}"
            )
        
        return page, page_size
    
    @staticmethod
    def calculate_offset(page: int, page_size: int) -> int:
        """
        Calculate offset for database query.
        
        Args:
            page: Page number
            page_size: Items per page
            
        Returns:
            Offset value for LIMIT/OFFSET
        """
        return (page - 1) * page_size
    
    @staticmethod
    def calculate_total_pages(total_items: int, page_size: int) -> int:
        """
        Calculate total number of pages.
        
        Args:
            total_items: Total number of items
            page_size: Items per page
            
        Returns:
            Total number of pages
        """
        import math
        return math.ceil(total_items / page_size)


# ============================================================================
# DATE VALIDATION LOGIC
# ============================================================================

class DateValidationLogic:
    """
    Business logic for date validations.
    """
    
    @staticmethod
    def validate_date_range(
        start_date: Optional[date],
        end_date: Optional[date],
        max_duration_days: int = BusinessRule.MAX_PROJECT_DURATION_DAYS
    ) -> None:
        """
        Validate date range for projects.
        
        Args:
            start_date: Project start date
            end_date: Project end date
            max_duration_days: Maximum allowed duration
            
        Raises:
            ValueError: If date range is invalid
        """
        now = datetime.now().date()
        
        # Check if end_date is before start_date
        if end_date and start_date and end_date < start_date:
            raise ValueError("End date must be on or after start date")
        
        # Check duration
        if start_date and end_date:
            duration = (end_date - start_date).days
            if duration > max_duration_days:
                raise ValueError(
                    f"Project duration cannot exceed {max_duration_days} days"
                )
        
        # Check for extremely distant future dates
        if start_date and end_date:
            far_future = now + DateValidationLogic.MIN_DATE_FUTURE
            if start_date > far_future or end_date > far_future:
                raise ValueError("Date cannot be more than 10 years in the future")
    
    @staticmethod
    def is_date_in_range(
        target_date: date,
        start_date: Optional[date],
        end_date: Optional[date]
    ) -> bool:
        """
        Check if a date falls within a date range.
        
        Args:
            target_date: Date to check
            start_date: Range start date
            end_date: Range end date
            
        Returns:
            True if date is within range
        """
        if start_date and target_date < start_date:
            return False
        if end_date and target_date > end_date:
            return False
        return True


# ============================================================================
# TASK STATUS TRANSITIONS
# ============================================================================

class TaskStatusTransition:
    """
    Business logic for task status transitions.
    """
    
    @staticmethod
    def is_valid_transition(
        current_status: str,
        new_status: str
    ) -> bool:
        """
        Check if task status transition is valid.
        
        Args:
            current_status: Current task status
            new_status: Target status
            
        Returns:
            True if transition is allowed
        """
        transitions = BusinessRule.VALID_TASK_TRANSITIONS
        return new_status in transitions.get(current_status, set())
    
    @staticmethod
    def get_previous_status(
        current_status: str
    ) -> Optional[str]:
        """
        Find the most likely previous status.
        
        Args:
            current_status: Current status
            
        Returns:
            Likely previous status or None
        """
        # Reverse mapping of transitions
        reverse_map: Dict[str, str] = {}
        for from_status, to_statuses in BusinessRule.VALID_TASK_TRANSITIONS.items():
            for to_status in to_statuses:
                if to_status not in reverse_map:
                    reverse_map[to_status] = from_status
        
        return reverse_map.get(current_status)


# ============================================================================
# GANTT CHART LOGIC
# ============================================================================

class GanttChartLogic:
    """
    Business logic for Gantt chart data operations.
    """
    
    @staticmethod
    def calculate_task_duration(
        start_date: date,
        end_date: date
    ) -> int:
        """
        Calculate task duration in days.
        
        Args:
            start_date: Task start date
            end_date: Task end date
            
        Returns:
            Duration in days
        """
        return (end_date - start_date).days + 1
    
    @staticmethod
    def calculate_progress(
        start_date: date,
        end_date: date,
        current_date: Optional[date] = None
    ) -> int:
        """
        Calculate expected progress based on timeline.
        
        Args:
            start_date: Task start date
            end_date: Task end date
            current_date: Current date (defaults to today)
            
        Returns:
            Progress percentage (0-100)
        """
        current = current_date or date.today()
        
        if current <= start_date:
            return 0
        if current >= end_date:
            return 100
        
        total_days = (end_date - start_date).days + 1
        elapsed_days = (current - start_date).days + 1
        
        return int((elapsed_days / total_days) * 100)
    
    @staticmethod
    def detect_schedule_conflicts(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Detect scheduling conflicts between tasks.
        
        Args:
            tasks: List of task dictionaries with start_date and end_date
            
        Returns:
            List of conflict descriptions
        """
        conflicts = []
        
        for i, task1 in enumerate(tasks):
            for task2 in tasks[i + 1:]:
                if task1.get('start_date') and task1.get('end_date'):
                    if task2.get('start_date') and task2.get('end_date'):
                        if DateValidationLogic.is_date_in_range(
                            task1['start_date'],
                            task2['start_date'],
                            task2['end_date']
                        ) or DateValidationLogic.is_date_in_range(
                            task2['start_date'],
                            task1['start_date'],
                            task1['end_date']
                        ):
                            conflicts.append({
                                'task1_id': task1['id'],
                                'task1_name': task1['name'],
                                'task2_id': task2['id'],
                                'task2_name': task2['name'],
                            })
        
        return conflicts


# ============================================================================
# VALIDATION LOGIC
# ============================================================================

class ValidationLogic:
    """
    Business logic for data validation operations.
    """
    
    @staticmethod
    def validate_name(name: str, max_length: int = 100) -> None:
        """
        Validate name field.
        
        Args:
            name: Name to validate
            max_length: Maximum allowed length
            
        Raises:
            ValueError: If validation fails
        """
        if not name or not name.strip():
            raise ValueError("Name cannot be empty")
        
        if len(name) > max_length:
            raise ValueError(f"Name cannot exceed {max_length} characters")
    
    @staticmethod
    def validate_email(email: str) -> None:
        """
        Validate email format.
        
        Args:
            email: Email to validate
            
        Raises:
            ValueError: If validation fails
        """
        from pydantic import EmailStr
        try:
            EmailStr.validate(email)
        except Exception as e:
            raise ValueError(f"Invalid email format: {str(e)}")
    
    @staticmethod
    def validate_project_name(name: str) -> None:
        """
        Validate project name.
        
        Args:
            name: Project name to validate
            
        Raises:
            ValueError: If validation fails
        """
        ValidationLogic.validate_name(name, max_length=200)
    
    @staticmethod
    def validate_description(description: Optional[str], max_length: int = 5000) -> None:
        """
        Validate description field.
        
        Args:
            description: Description to validate
            max_length: Maximum allowed length
            
        Raises:
            ValueError: If validation fails
        """
        if description is None:
            return
        
        if len(description) > max_length:
            raise ValueError(
                f"Description cannot exceed {max_length} characters"
            )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def generate_user_id() -> str:
    """
    Generate a unique user ID.
    
    Returns:
        Unique user ID string
    """
    import uuid
    return f"usr_{uuid.uuid4().hex[:12]}"


def generate_project_id() -> str:
    """
    Generate a unique project ID.
    
    Returns:
        Unique project ID string
    """
    import uuid
    return f"proj_{uuid.uuid4().hex[:12]}"


def generate_task_id() -> str:
    """
    Generate a unique task ID.
    
    Returns:
        Unique task ID string
    """
    import uuid
    return f"task_{uuid.uuid4().hex[:12]}"


def generate_milestone_id() -> str:
    """
    Generate a unique milestone ID.
    
    Returns:
        Unique milestone ID string
    """
    import uuid
    return f"mile_{uuid.uuid4().hex[:12]}"


def generate_event_id() -> str:
    """
    Generate a unique event ID.
    
    Returns:
        Unique event ID string
    """
    import uuid
    return f"evnt_{uuid.uuid4().hex[:12]}"
