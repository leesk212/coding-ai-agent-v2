"""
Exception Handling Standards for Project Management System.

This module defines custom exceptions and error handling patterns
following Python best practices and the error specifications from OpenAPI.
"""

from typing import Optional, Dict, Any
from enum import Enum
from http import HTTPStatus


# ============================================================================
# ERROR CODES ENUMERATION
# ============================================================================

class ErrorCode(Enum):
    """
    Standardized error codes for the PMS API.
    
    These codes should be used consistently across all error responses
    to enable client-side error handling.
    """
    # Authentication Errors (401)
    UNAUTHORIZED = "UNAUTHORIZED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_TOKEN = "INVALID_TOKEN"
    TOKEN_REQUIRED = "TOKEN_REQUIRED"
    
    # Authorization Errors (403)
    FORBIDDEN = "FORBIDDEN"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    CANNOT_DELETE_PROJECT = "CANNOT_DELETE_PROJECT"
    CANNOT_ACCESS_RESOURCE = "CANNOT_ACCESS_RESOURCE"
    
    # Validation Errors (400)
    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_REQUEST = "INVALID_REQUEST"
    INVALID_DATE_RANGE = "INVALID_DATE_RANGE"
    INVALID_STATUS_TRANSITION = "INVALID_STATUS_TRANSITION"
    PASSWORD_WEAK = "PASSWORD_WEAK"
    EMAIL_EXISTS = "EMAIL_EXISTS"
    
    # Resource Errors (404)
    USER_NOT_FOUND = "USER_NOT_FOUND"
    PROJECT_NOT_FOUND = "PROJECT_NOT_FOUND"
    TASK_NOT_FOUND = "TASK_NOT_FOUND"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    
    # Conflict Errors (409)
    EMAIL_ALREADY_EXISTS = "EMAIL_ALREADY_EXISTS"
    USERNAME_TAKEN = "USERNAME_TAKEN"
    
    # Rate Limiting Errors (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    TOO_MANY_LOGIN_ATTEMPTS = "TOO_MANY_LOGIN_ATTEMPTS"
    
    # Server Errors (500)
    INTERNAL_ERROR = "INTERNAL_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"


# ============================================================================
# BASE EXCEPTION CLASS
# ============================================================================

class PMSException(Exception):
    """
    Base exception class for all PMS exceptions.
    
    This is the parent class for all custom exceptions in the system.
    It provides a standard interface for error handling.
    
    Attributes:
        error_code: Machine-readable error code
        message: Human-readable error message
        details: Additional error details (optional)
        status_code: HTTP status code
    """
    
    error_code = ErrorCode.INTERNAL_ERROR
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize PMSException.
        
        Args:
            message: Human-readable error message
            details: Additional error details (optional)
            original_exception: Original exception for chaining (optional)
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.original_exception = original_exception
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary format for API response.
        
        Returns:
            Dictionary with error code, message, and details
        """
        result = {
            "error": self.error_code.value,
            "message": self.message,
        }
        if self.details:
            result["details"] = self.details
        return result
    
    def __str__(self) -> str:
        """String representation of the exception."""
        return self.message


# ============================================================================
# CLIENT ERROR EXCEPTIONS (4xx)
# ============================================================================

class ClientError(PMSException):
    """
    Base class for client errors (4xx status codes).
    
    These exceptions indicate that the client made an error
    in their request.
    """
    pass


class AuthenticationError(ClientError):
    """
    Base exception for authentication errors.
    
    Raised when authentication fails or credentials are invalid.
    """
    status_code = HTTPStatus.UNAUTHORIZED


class UnauthorizedError(AuthenticationError):
    """
    Exception for unauthorized access attempts.
    
    Raised when a valid token is provided but doesn't grant access.
    """
    error_code = ErrorCode.UNAUTHORIZED
    message = "Unauthorized access"


class TokenRequiredError(AuthenticationError):
    """
    Exception when authentication token is required.
    """
    error_code = ErrorCode.TOKEN_REQUIRED
    message = "Authentication token required"


class InvalidCredentialsError(AuthenticationError):
    """
    Exception for invalid login credentials.
    """
    error_code = ErrorCode.INVALID_CREDENTIALS
    message = "Invalid email or password"


class TokenExpiredError(AuthenticationError):
    """
    Exception for expired authentication token.
    """
    error_code = ErrorCode.TOKEN_EXPIRED
    message = "Authentication token has expired"


class InvalidTokenError(AuthenticationError):
    """
    Exception for invalid authentication token.
    """
    error_code = ErrorCode.INVALID_TOKEN
    message = "Invalid authentication token"


class AuthorizationError(ClientError):
    """
    Base exception for authorization errors.
    
    Raised when user lacks permission to perform an action.
    """
    status_code = HTTPStatus.FORBIDDEN


class ForbiddenError(AuthorizationError):
    """
    Exception for forbidden access attempts.
    """
    error_code = ErrorCode.FORBIDDEN
    message = "Access forbidden"


class InsufficientPermissionsError(AuthorizationError):
    """
    Exception for insufficient user permissions.
    """
    error_code = ErrorCode.INSUFFICIENT_PERMISSIONS
    message = "Insufficient permissions to perform this action"


class CannotDeleteProjectError(AuthorizationError):
    """
    Exception when PM tries to delete a project.
    
    Only Admins can delete projects.
    """
    error_code = ErrorCode.CANNOT_DELETE_PROJECT
    message = "Only administrators can delete projects"


class ResourceNotFoundError(ClientError):
    """
    Base exception for resource not found errors.
    """
    status_code = HTTPStatus.NOT_FOUND


class UserNotFoundError(ResourceNotFoundError):
    """
    Exception when user is not found.
    """
    error_code = ErrorCode.USER_NOT_FOUND
    message = "User not found"


class ProjectNotFoundError(ResourceNotFoundError):
    """
    Exception when project is not found.
    """
    error_code = ErrorCode.PROJECT_NOT_FOUND
    message = "Project not found"


class TaskNotFoundError(ResourceNotFoundError):
    """
    Exception when task is not found.
    """
    error_code = ErrorCode.TASK_NOT_FOUND
    message = "Task not found"


class ValidationClientError(ClientError):
    """
    Base exception for validation errors.
    """
    status_code = HTTPStatus.BAD_REQUEST


class ValidationError(ValidationClientError):
    """
    Exception for general validation errors.
    """
    error_code = ErrorCode.VALIDATION_ERROR
    message = "Request validation failed"


class InvalidRequestError(ValidationClientError):
    """
    Exception for invalid request format.
    """
    error_code = ErrorCode.INVALID_REQUEST
    message = "Invalid request format"


class InvalidDateRangeError(ValidationClientError):
    """
    Exception for invalid date range.
    """
    error_code = ErrorCode.INVALID_DATE_RANGE
    message = "Invalid date range"


class InvalidStatusTransitionError(ValidationClientError):
    """
    Exception for invalid status transition.
    """
    error_code = ErrorCode.INVALID_STATUS_TRANSITION
    message = "Invalid status transition"


class PasswordWeakError(ValidationClientError):
    """
    Exception for weak password.
    """
    error_code = ErrorCode.PASSWORD_WEAK
    message = "Password does not meet strength requirements"


class EmailExistsError(ValidationClientError):
    """
    Exception when email already exists.
    """
    error_code = ErrorCode.EMAIL_EXISTS
    message = "Email already exists"


class ConflictError(ClientError):
    """
    Base exception for conflict errors (409).
    
    Raised when request conflicts with current server state.
    """
    status_code = HTTPStatus.CONFLICT


class EmailAlreadyExistsError(ConflictError):
    """
    Exception when registering with existing email.
    """
    error_code = ErrorCode.EMAIL_ALREADY_EXISTS
    message = "Email already exists"


class RateLimitError(ClientError):
    """
    Base exception for rate limit errors (429).
    
    Raised when client exceeds rate limits.
    """
    status_code = HTTPStatus.TOO_MANY_REQUESTS


class RateLimitExceededError(RateLimitError):
    """
    Exception for rate limit exceeded.
    """
    error_code = ErrorCode.RATE_LIMIT_EXCEEDED
    message = "Rate limit exceeded. Please try again later."


class TooManyLoginAttemptsError(RateLimitError):
    """
    Exception for too many failed login attempts.
    """
    error_code = ErrorCode.TOO_MANY_LOGIN_ATTEMPTS
    message = "Too many failed login attempts. Account temporarily locked."


# ============================================================================
# SERVER ERROR EXCEPTIONS (5xx)
# ============================================================================

class ServerError(PMSException):
    """
    Base class for server errors (5xx status codes).
    
    These exceptions indicate an error on the server side.
    """
    status_code = HTTPStatus.INTERNAL_SERVER_ERROR


class InternalServerError(ServerError):
    """
    Exception for general server errors.
    """
    error_code = ErrorCode.INTERNAL_ERROR
    message = "An internal server error occurred"


class DatabaseError(ServerError):
    """
    Exception for database errors.
    """
    error_code = ErrorCode.DATABASE_ERROR
    message = "A database error occurred"


class ServiceUnavailableError(ServerError):
    """
    Exception for service unavailable.
    """
    error_code = ErrorCode.SERVICE_UNAVAILABLE
    status_code = HTTPStatus.SERVICE_UNAVAILABLE
    message = "Service temporarily unavailable"


# ============================================================================
# BUSINESS LOGIC EXCEPTIONS
# ============================================================================

class BusinessException(PMSException):
    """
    Base exception for business logic errors.
    
    Raised when business rules are violated.
    """
    status_code = HTTPStatus.BAD_REQUEST


class ProjectStatusError(BusinessException):
    """
    Exception for invalid project status operations.
    """
    error_code = ErrorCode.INVALID_STATUS_TRANSITION
    message = "Invalid project status operation"


class TaskStatusError(BusinessException):
    """
    Exception for invalid task status operations.
    """
    error_code = ErrorCode.INVALID_STATUS_TRANSITION
    message = "Invalid task status operation"


# ============================================================================
# EXCEPTION HANDLING UTILITIES
# ============================================================================

def map_exception_to_error(
    exception: Exception,
    default_code: ErrorCode = ErrorCode.INTERNAL_ERROR
) -> tuple[ErrorCode, str, Dict[str, Any]]:
    """
    Map an exception to error code, message, and details.
    
    This function helps convert exceptions to standardized error responses.
    
    Args:
        exception: The exception to map
        default_code: Default error code if mapping fails
        
    Returns:
        Tuple of (error_code, message, details)
    """
    if isinstance(exception, PMSException):
        return (
            exception.error_code,
            exception.message,
            exception.details,
        )
    
    # Map common exceptions
    error_map = {
        ValueError: (ErrorCode.VALIDATION_ERROR, "Invalid value", {}),
        TypeError: (ErrorCode.INVALID_REQUEST, "Invalid type", {}),
        KeyError: (ErrorCode.INVALID_REQUEST, "Missing required field", {}),
        PermissionError: (ErrorCode.FORBIDDEN, "Permission denied", {}),
    }
    
    for exc_type, (code, message, details) in error_map.items():
        if isinstance(exception, exc_type):
            return (code, message, details)
    
    # Default to internal error
    return (default_code, str(exception), {})


def safe_execute(
    func,
    *args,
    default=None,
    error_handler=None,
    **kwargs
):
    """
    Safely execute a function with exception handling.
    
    This utility wraps function execution with proper exception handling
    and returns a default value on failure.
    
    Args:
        func: Function to execute
        *args: Positional arguments for the function
        default: Default value to return on error
        error_handler: Optional handler function for exceptions
        **kwargs: Keyword arguments for the function
        
    Returns:
        Function result or default value on error
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if error_handler:
            return error_handler(e)
        return default


# ============================================================================
# EXCEPTION DECORATORS
# ============================================================================

from functools import wraps
import logging

logger = logging.getLogger(__name__)


def handle_exceptions(
    default_response: Optional[Dict[str, Any]] = None
):
    """
    Decorator to handle exceptions in a function.
    
    Catches all exceptions, logs them, and returns a standardized error response.
    
    Args:
        default_response: Default response to return on error (optional)
        
    Returns:
        Decorated function with exception handling
        
    Example:
        @handle_exceptions(default_response={"error": "Failed to process"})
        def my_function(arg):
            # function logic
            pass
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except PMSException as e:
                logger.warning(
                    f"PMSException in {func.__name__}: {e.message}",
                    exc_info=True
                )
                if default_response:
                    return default_response
                return {"error": e.error_code.value, "message": e.message}
            except Exception as e:
                logger.error(
                    f"Unexpected exception in {func.__name__}: {str(e)}",
                    exc_info=True
                )
                if default_response:
                    return default_response
                return {"error": ErrorCode.INTERNAL_ERROR.value, "message": "Internal server error"}
        return wrapper
    return decorator


def log_exception_on_error(func):
    """
    Decorator to log exceptions before re-raising.
    
    Useful for wrapping functions that should log errors
    but still propagate the exception.
    
    Args:
        func: Function to decorate
        
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Exception in {func.__name__}: {str(e)}")
            raise
    return wrapper
