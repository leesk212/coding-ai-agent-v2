"""
Core module for Project Management System.
"""

from .exceptions import (
    # Error codes
    ErrorCode,
    
    # Base exceptions
    PMSException,
    ClientError,
    ServerError,
    BusinessException,
    
    # Authentication exceptions
    AuthenticationError,
    UnauthorizedError,
    TokenRequiredError,
    InvalidCredentialsError,
    TokenExpiredError,
    InvalidTokenError,
    
    # Authorization exceptions
    AuthorizationError,
    ForbiddenError,
    InsufficientPermissionsError,
    CannotDeleteProjectError,
    
    # Resource exceptions
    ResourceNotFoundError,
    UserNotFoundError,
    ProjectNotFoundError,
    TaskNotFoundError,
    
    # Validation exceptions
    ValidationClientError,
    ValidationError,
    InvalidRequestError,
    InvalidDateRangeError,
    InvalidStatusTransitionError,
    PasswordWeakError,
    EmailExistsError,
    
    # Conflict exceptions
    ConflictError,
    EmailAlreadyExistsError,
    
    # Rate limit exceptions
    RateLimitError,
    RateLimitExceededError,
    TooManyLoginAttemptsError,
    
    # Server exceptions
    InternalServerError,
    DatabaseError,
    ServiceUnavailableError,
    
    # Business logic exceptions
    ProjectStatusError,
    TaskStatusError,
    
    # Utilities
    map_exception_to_error,
    safe_execute,
    handle_exceptions,
    log_exception_on_error,
)

from .auth import (
    # Password hashing
    hash_password,
    verify_password,
    
    # JWT tokens
    create_access_token,
    decode_access_token,
    verify_token,
    
    # Authentication dependencies
    get_current_user,
    get_current_active_user,
    
    # Authorization decorators
    require_permission,
    require_role,
    require_admin,
    require_owner,
    
    # Services
    AuthService,
    
    # Rate limiting
    LoginRateLimiter,
    login_rate_limiter,
    
    # Settings
    AuthSettings,
)

__all__ = [
    # Error codes
    'ErrorCode',
    
    # Base exceptions
    'PMSException',
    'ClientError',
    'ServerError',
    'BusinessException',
    
    # Authentication exceptions
    'AuthenticationError',
    'UnauthorizedError',
    'TokenRequiredError',
    'InvalidCredentialsError',
    'TokenExpiredError',
    'InvalidTokenError',
    
    # Authorization exceptions
    'AuthorizationError',
    'ForbiddenError',
    'InsufficientPermissionsError',
    'CannotDeleteProjectError',
    
    # Resource exceptions
    'ResourceNotFoundError',
    'UserNotFoundError',
    'ProjectNotFoundError',
    'TaskNotFoundError',
    
    # Validation exceptions
    'ValidationClientError',
    'ValidationError',
    'InvalidRequestError',
    'InvalidDateRangeError',
    'InvalidStatusTransitionError',
    'PasswordWeakError',
    'EmailExistsError',
    
    # Conflict exceptions
    'ConflictError',
    'EmailAlreadyExistsError',
    
    # Rate limit exceptions
    'RateLimitError',
    'RateLimitExceededError',
    'TooManyLoginAttemptsError',
    
    # Server exceptions
    'InternalServerError',
    'DatabaseError',
    'ServiceUnavailableError',
    
    # Business logic exceptions
    'ProjectStatusError',
    'TaskStatusError',
    
    # Utilities
    'map_exception_to_error',
    'safe_execute',
    'handle_exceptions',
    'log_exception_on_error',
    
    # Auth
    'hash_password',
    'verify_password',
    'create_access_token',
    'decode_access_token',
    'verify_token',
    'get_current_user',
    'get_current_active_user',
    'require_permission',
    'require_role',
    'require_admin',
    'require_owner',
    'AuthService',
    'LoginRateLimiter',
    'login_rate_limiter',
    'AuthSettings',
]
