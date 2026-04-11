"""
Python Error Handling Best Practices
=====================================

This module demonstrates recommended error handling patterns based on Python
community best practices and PEP guidelines.
"""

import logging
from contextlib import contextmanager
from typing import Generator, Optional
import time
from functools import wraps

# Configure logging for production-grade error handling
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# 1. Custom Exception Classes
# =============================================================================

class ApplicationError(Exception):
    """Base exception for application-specific errors."""
    
    def __init__(self, message: str, code: Optional[str] = None, 
                 details: Optional[dict] = None):
        self.code = code
        self.details = details or {}
        super().__init__(message)


class ValidationError(ApplicationError):
    """Raised when input validation fails."""
    pass


class ConfigurationError(ApplicationError):
    """Raised when configuration issues occur."""
    pass


class ResourceNotFoundError(ApplicationError):
    """Raised when a requested resource is not found."""
    pass


# =============================================================================
# 2. Proper Exception Hierarchy
# =============================================================================

class DataLayerError(Exception):
    """Base exception for data layer operations."""
    pass


class DatabaseConnectionError(DataLayerError):
    """Raised when database connection fails."""
    pass


class QueryExecutionError(DataLayerError):
    """Raised when a database query fails."""
    pass


class IntegrityError(DataLayerError):
    """Raised when data integrity constraints are violated."""
    pass


# =============================================================================
# 3. Complete Try/Except/Finally/Else Pattern
# =============================================================================

def safe_divide(numerator: float, denominator: float) -> float:
    """
    Demonstrates complete exception handling pattern with:
    - try: code that may raise exceptions
    - except: specific exception handling
    - else: runs only if no exception occurred
    - finally: always executes (cleanup)
    """
    logger.info(f"Dividing {numerator} by {denominator}")
    
    try:
        result = numerator / denominator
    except ZeroDivisionError as e:
        logger.error(f"Division by zero prevented: {e}")
        raise ApplicationError(
            message="Cannot divide by zero",
            code="DIV_ZERO",
            details={"numerator": numerator, "denominator": denominator}
        ) from e
    except TypeError as e:
        logger.error(f"Invalid types provided: {e}")
        raise ApplicationError(
            message="Invalid input types for division",
            code="INVALID_TYPE",
            details={"numerator_type": type(numerator).__name__,
                    "denominator_type": type(denominator).__name__}
        ) from e
    else:
        logger.info("Division successful")
        return result
    finally:
        logger.debug("Division operation completed")


# =============================================================================
# 4. Exception Chaining (Using 'raise ... from')
# =============================================================================

def fetch_data_source(source_id: str) -> dict:
    """Simulate fetching data with proper exception chaining."""
    try:
        # Simulate potential failure
        if source_id == "invalid":
            raise ValueError("Invalid source ID")
        return {"id": source_id, "data": "sample"}
    except ValueError as e:
        # Chain the original exception for debugging context
        raise ResourceNotFoundError(
            f"Could not fetch data for source: {source_id}"
        ) from e


# =============================================================================
# 5. Catching Specific Exceptions (NOT bare 'except:')
# =============================================================================

def process_config(config_path: str) -> dict:
    """
    Best practice: Catch specific exceptions, not bare 'except:'.
    This prevents hiding unexpected errors like KeyboardInterrupt.
    """
    try:
        with open(config_path, 'r') as f:
            return eval(f.read())  # Simplified for demo
    except FileNotFoundError as e:
        logger.error(f"Config file not found: {config_path}")
        raise ConfigurationError(
            message="Configuration file missing",
            code="CONFIG_NOT_FOUND",
            details={"path": config_path}
        ) from e
    except PermissionError as e:
        logger.error(f"Permission denied accessing config: {config_path}")
        raise ConfigurationError(
            message="Permission denied for config file",
            code="CONFIG_PERMISSION",
            details={"path": config_path}
        ) from e
    except SyntaxError as e:
        logger.error(f"Invalid config syntax at line {e.lineno}: {e.msg}")
        raise ConfigurationError(
            message="Invalid configuration syntax",
            code="CONFIG_SYNTAX",
            details={"line": e.lineno, "column": e.offset, "path": config_path}
        ) from e


# =============================================================================
# 6. Using context managers for Resource Management
# =============================================================================

@contextmanager
def safe_file_operation(filepath: str, mode: str = 'r') -> Generator:
    """
    Context manager that handles file operations safely with proper
    error handling and cleanup.
    """
    file_handle = None
    try:
        logger.info(f"Opening file: {filepath}")
        file_handle = open(filepath, mode)
        yield file_handle
    except FileNotFoundError as e:
        logger.error(f"File not found: {filepath}")
        raise
    except PermissionError as e:
        logger.error(f"Permission denied: {filepath}")
        raise
    except Exception as e:
        logger.error(f"Error during file operation: {e}")
        raise
    finally:
        if file_handle is not None:
            try:
                file_handle.close()
                logger.debug(f"Closed file: {filepath}")
            except Exception as e:
                logger.warning(f"Failed to close file properly: {e}")


# =============================================================================
# 7. Using 'raise from' for Exception Context Preservation
# =============================================================================

def validate_and_process(value: str) -> int:
    """Demonstrates preserving exception context through call chains."""
    try:
        # Nested operation that may fail
        numeric_value = int(value)
    except ValueError as e:
        # Preserve original exception context
        raise ValidationError(
            f"Cannot convert '{value}' to integer"
        ) from e
    
    if numeric_value <= 0:
        raise ValidationError(
            "Value must be positive"
        )
    
    return numeric_value


# =============================================================================
# 8. Multiple Exception Types Handling
# =============================================================================

def process_request(request: dict) -> dict:
    """
    Demonstrates handling multiple related exception types
    with a single handler while still distinguishing them.
    """
    try:
        method = request.get('method')
        data = request.get('data')
        
        if method not in ('create', 'update', 'delete'):
            raise ValidationError(f"Invalid method: {method}")
        
        if not data:
            raise ValidationError("Missing data")
        
        # Simulate processing
        return {"status": "success", "method": method}
    
    except (ValidationError, KeyError, TypeError) as e:
        # Group related exceptions
        logger.warning(f"Invalid request: {type(e).__name__}: {e}")
        return {
            "status": "error",
            "error_code": "INVALID_REQUEST",
            "message": str(e)
        }


# =============================================================================
# 9. Retry Logic with Exponential Backoff
# =============================================================================

def retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator for retrying operations with exponential backoff.
    Only retries on transient (temporary) errors.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except (
                    DatabaseConnectionError,
                    QueryExecutionError
                ) as e:
                    last_exception = e
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}"
                    )
                    
                    if attempt < max_attempts - 1:
                        logger.info(f"Retrying in {current_delay:.1f}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}"
                        )
            
            # Raise the last exception after all retries exhausted
            raise last_exception
        
        return wrapper
    return decorator


# =============================================================================
# 10. Production-Grade Error Handler
# =============================================================================

class ErrorHandler:
    """
    Centralized error handling utility for production applications.
    Handles logging, error formatting, and exception classification.
    """
    
    def __init__(self):
        self._error_registry = {}
    
    def log_error(
        self, 
        error: Exception, 
        context: Optional[dict] = None,
        level: str = "ERROR"
    ) -> dict:
        """
        Log an error with structured context information.
        
        Args:
            error: The exception that occurred
            context: Additional context about the error
            level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
        Returns:
            dict: Structured error information
        """
        error_info = {
            "type": type(error).__name__,
            "message": str(error),
            "context": context or {},
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        }
        
        # Handle exception chaining
        if error.__cause__ is not None:
            error_info["cause"] = {
                "type": type(error.__cause__).__name__,
                "message": str(error.__cause__)
            }
        
        # Log at appropriate level
        log_method = getattr(logger, level.lower(), logger.error)
        log_method(
            f"{type(error).__name__}: {error}",
            extra={"error_info": error_info},
            exc_info=True
        )
        
        return error_info
    
    def create_error_response(
        self, 
        error: Exception, 
        http_status: int = 500
    ) -> dict:
        """
        Create a user-friendly error response.
        
        Best practice: Never expose internal error details to end users.
        """
        # In production, map errors to generic messages
        error_map = {
            "ValidationError": ("Invalid input provided", 400),
            "ConfigurationError": ("Configuration error occurred", 500),
            "ResourceNotFoundError": ("Requested resource not found", 404),
            "DatabaseConnectionError": ("Database temporarily unavailable", 503),
        }
        
        error_type = type(error).__name__
        if error_type in error_map:
            message, status = error_map[error_type]
        else:
            message = "An unexpected error occurred"
            status = 500
        
        return {
            "success": False,
            "error": {
                "code": getattr(error, 'code', 'UNKNOWN_ERROR'),
                "message": message,
            },
            "status": status
        }


# =============================================================================
# 11. Main Demo
# =============================================================================

def main():
    """Demonstrate various error handling patterns."""
    
    print("=" * 60)
    print("Python Error Handling Best Practices Demo")
    print("=" * 60)
    
    # Example 1: Custom exceptions with error codes
    print("\n1. Custom Exception with Error Code:")
    try:
        raise ValidationError(
            "Invalid email format",
            code="VALIDATION_EMAIL",
            details={"field": "email", "value": "not-an-email"}
        )
    except ValidationError as e:
        print(f"   Error Code: {e.code}")
        print(f"   Message: {e}")
        print(f"   Details: {e.details}")
    
    # Example 2: Exception chaining
    print("\n2. Exception Chaining (raise ... from):")
    try:
        fetch_data_source("invalid")
    except ResourceNotFoundError as e:
        print(f"   Caught: {e}")
        print(f"   Original cause: {e.__cause__}")
    
    # Example 3: Complete try/except/else/finally
    print("\n3. Complete Exception Handling:")
    result = safe_divide(10, 2)
    print(f"   10 / 2 = {result}")
    
    # Example 4: Multiple exception handling
    print("\n4. Multiple Exception Types:")
    response = process_request({"method": "create", "data": {"key": "value"}})
    print(f"   Response: {response}")
    
    # Example 5: Retry decorator
    print("\n5. Retry Logic with Exponential Backoff:")
    
    @retry(max_attempts=3, delay=0.1, backoff=2.0)
    def flaky_operation():
        import random
        if random.random() < 0.7:
            raise DatabaseConnectionError("Database unavailable")
        return "success"
    
    try:
        result = flaky_operation()
        print(f"   Operation succeeded: {result}")
    except DatabaseConnectionError as e:
        print(f"   Operation failed after retries: {e}")
    
    # Example 6: Production error handling
    print("\n6. Production-Grade Error Handling:")
    handler = ErrorHandler()
    try:
        raise DatabaseConnectionError("Connection timeout")
    except Exception as e:
        error_info = handler.log_error(e, context={"db_host": "localhost"})
        response = handler.create_error_response(e, http_status=503)
        print(f"   HTTP Status: {response['status']}")
        print(f"   Error Code: {response['error']['code']}")
        print(f"   User Message: {response['error']['message']}")
    
    print("\n" + "=" * 60)
    print("Demo Complete")
    print("=" * 60)


if __name__ == "__main__":
    main()
