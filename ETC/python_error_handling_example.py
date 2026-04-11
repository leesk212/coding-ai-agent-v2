"""
Python Error Handling Best Practices Example

Demonstrates comprehensive error handling patterns including custom exceptions,
retry logic, context managers, and layered error handling.
"""

import logging
import time
import random
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Optional, Any, NoReturn
from datetime import datetime, timezone

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# =============================================================================
# Custom Exception Hierarchy
# =============================================================================

class DataProcessingError(Exception):
    """Base exception for data processing errors."""

    def __init__(self, message: str, context: Optional[dict[str, Any]] = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or {}


class ValidationError(DataProcessingError):
    """Raised when input data fails validation rules."""

    pass


class DatabaseError(DataProcessingError):
    """Raised when database operations fail."""

    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    pass


class ProcessingError(DataProcessingError):
    """Raised when data transformation fails."""

    pass


# =============================================================================
# Retry Logic with Exponential Backoff and Jitter
# =============================================================================

def retry_on_error(
    exceptions: tuple[type[Exception], ...] = (Exception,),
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    jitter: float = 0.5
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Decorator for retrying functions with exponential backoff and jitter.

    Args:
        exceptions: Tuple of exception types to catch and retry on.
        max_attempts: Maximum number of retry attempts.
        base_delay: Initial delay in seconds before first retry.
        max_delay: Maximum delay cap in seconds.
        jitter: Random multiplier for additional randomness (0.0 to 1.0).

    Returns:
        Decorator function that wraps the target function.

    Example:
        @retry_on_error(exceptions=(DatabaseError,), max_attempts=5)
        def fetch_data(): ...
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception: Optional[Exception] = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    delay = min(base_delay * (2 ** (attempt - 1)), max_delay)
                    # Add random jitter to prevent thundering herd
                    jittered_delay = delay * (1 + random.random() * jitter)
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {jittered_delay:.2f}s",
                        exc_info=True
                    )
                    
                    if attempt < max_attempts:
                        time.sleep(jittered_delay)
            
            # All attempts failed - re-raise with chaining
            if last_exception is not None:
                logger.error(
                    f"All {max_attempts} attempts failed for {func.__name__}",
                    exc_info=True
                )
                raise last_exception
        
        return wrapper
    
    return decorator


# =============================================================================
# Resource Management with Context Managers
# =============================================================================

@contextmanager
def resource_manager(resource_name: str) -> Callable[[], None]:
    """
    Context manager for handling resource lifecycle with proper cleanup.

    Args:
        resource_name: Name of the resource for logging purposes.

    Yields:
        Resource identifier for use within the context.

    Raises:
        RuntimeError: If resource initialization fails.
    """
    resource_id: Optional[str] = None
    logger.info(f"Initializing resource: {resource_name}")
    
    try:
        # Simulate resource acquisition
        resource_id = f"{resource_name}_{int(time.time())}"
        logger.debug(f"Resource {resource_id} acquired")
        yield resource_id
    except Exception as e:
        logger.error(f"Error processing with {resource_name}: {e}", exc_info=True)
        raise
    finally:
        # Cleanup happens regardless of success or failure
        if resource_id:
            logger.info(f"Cleaning up resource: {resource_id}")
            # Simulate resource release
        logger.info(f"Resource {resource_name} lifecycle complete")


# =============================================================================
# Validation Layer
# =============================================================================

def validate_input(data: dict[str, Any]) -> None:
    """
    Validate input data against expected schema and constraints.

    Args:
        data: Dictionary containing input data to validate.

    Raises:
        ValidationError: If any validation check fails.
    """
    required_fields = ['name', 'value']
    
    for field in required_fields:
        if field not in data:
            error_msg = f"Missing required field: {field}"
            logger.error(error_msg)
            raise ValidationError(error_msg, context={'missing_field': field})
    
    if not isinstance(data.get('name'), str):
        error_msg = "Field 'name' must be a string"
        logger.error(error_msg, exc_info=False)
        raise ValidationError(error_msg, context={'field': 'name', 'expected': 'str'})
    
    if not isinstance(data.get('value'), (int, float)):
        error_msg = "Field 'value' must be a numeric type"
        logger.error(error_msg)
        raise ValidationError(error_msg, context={'field': 'value', 'expected': 'numeric'})
    
    if data.get('value') < 0:
        error_msg = "Field 'value' must be non-negative"
        logger.error("Validation failed: value < 0")
        raise ValidationError(error_msg, context={'field': 'value', 'value': data['value']})


# =============================================================================
# Processing Layer
# =============================================================================

@retry_on_error(
    exceptions=(ProcessingError,),
    max_attempts=3,
    base_delay=0.5,
    max_delay=5.0
)
def process_data(data: dict[str, Any]) -> dict[str, Any]:
    """
    Process validated data with transformation logic.

    Args:
        data: Validated input data dictionary.

    Returns:
        Processed data with computed results.

    Raises:
        ProcessingError: If transformation fails.
    """
    try:
        result = {
            'name': data['name'],
            'processed_value': data['value'] * 2,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'status': 'success'
        }
        logger.info(f"Successfully processed data for {data['name']}")
        return result
    except Exception as e:
        # Exception chaining preserves original error context
        logger.exception("Processing failed for data")
        raise ProcessingError(
            f"Failed to process data: {e}",
            context={'original_error': str(e)}
        ) from e


# =============================================================================
# Database Layer (Boundary Layer)
# =============================================================================

class DataStore:
    """Database abstraction with error handling at the boundary layer."""

    def __init__(self, connection_string: str) -> None:
        """
        Initialize the data store.

        Args:
            connection_string: Database connection string.
        """
        self.connection_string = connection_string
        self._connection: Optional[str] = None

    @retry_on_error(
        exceptions=(ConnectionError, DatabaseError),
        max_attempts=5,
        base_delay=1.0,
        max_delay=30.0,
        jitter=0.3
    )
    def connect(self) -> None:
        """Establish database connection with retry logic."""
        if self._connection:
            logger.warning("Already connected")
            return
        
        # Simulate connection failure scenario
        if random.random() < 0.3:
            error_msg = "Database connection refused"
            logger.error(error_msg)
            raise ConnectionError(error_msg) from Exception("Connection refused")
        
        self._connection = "connected"
        logger.info("Database connection established")

    def save(self, data: dict[str, Any]) -> str:
        """
        Save processed data to the database.

        Args:
            data: Processed data to persist.

        Returns:
            Record identifier.

        Raises:
            DatabaseError: If save operation fails.
        """
        if not self._connection:
            raise DatabaseError("Not connected to database", context={'action': 'save'})
        
        try:
            record_id = f"record_{int(time.time())}_{random.randint(1000, 9999)}"
            logger.info(f"Saved record: {record_id}")
            return record_id
        except Exception as e:
            raise DatabaseError(f"Failed to save record: {e}", context={'data': data}) from e

    def close(self) -> None:
        """Close the database connection safely."""
        if self._connection:
            logger.info("Closing database connection")
            self._connection = None


# =============================================================================
# Main Application Layer
# =============================================================================

def handle_single_error() -> NoReturn:
    """
    Demonstrate handling of a single error with proper logging.

    This function never returns successfully, raising an error instead.

    Raises:
        ValidationError: Always raised to demonstrate error handling.
    """
    try:
        validate_input({'incomplete': 'data'})
    except ValidationError as e:
        logger.error(f"Validation error caught and handled: {e}")
        raise


def handle_error_chain() -> dict[str, Any]:
    """
    Demonstrate exception chaining through multiple layers.

    Returns:
        Processed data result.

    Raises:
        ProcessingError: May be raised if processing fails.
    """
    try:
        data = {'name': 'example', 'value': 42}
        validate_input(data)
        result = process_data(data)
        return result
    except ValidationError as e:
        logger.exception("Validation error in chain")
        raise
    except ProcessingError as e:
        logger.exception("Processing error in chain")
        raise


def handle_error_with_resources() -> dict[str, Any]:
    """
    Demonstrate error handling with proper resource management.

    Uses context manager to ensure resources are cleaned up properly.

    Returns:
        Processed data result.
    """
    store = DataStore("postgres://localhost")
    
    with resource_manager("data_pipeline") as resource_id:
        try:
            store.connect()
            data = {'name': 'resource_test', 'value': 100}
            validate_input(data)
            processed = process_data(data)
            record_id = store.save(processed)
            
            logger.info(f"Complete pipeline result: {record_id}")
            return {**processed, 'record_id': record_id, 'resource': resource_id}
        
        except (ValidationError, ProcessingError, DatabaseError) as e:
            logger.error(f"Pipeline error: {type(e).__name__}: {e}")
            raise
        
        finally:
            store.close()


def demonstrate_error_handling() -> None:
    """Run demonstrations of various error handling patterns."""
    print("=" * 60)
    print("Python Error Handling Best Practices Demo")
    print("=" * 60)

    # Demo 1: Exception chaining
    print("\n1. Exception Chaining:")
    try:
        handle_error_chain()
    except Exception as e:
        print(f"   Caught: {type(e).__name__}: {e}")

    # Demo 2: Retry with exponential backoff
    print("\n2. Retry with Exponential Backoff:")
    try:
        result = handle_error_with_resources()
        print(f"   Success: {result.get('status')}")
    except Exception as e:
        print(f"   Failed after retries: {type(e).__name__}")

    # Demo 3: Custom exception hierarchy
    print("\n3. Custom Exception Hierarchy:")
    try:
        raise ValidationError("Test validation error", context={'key': 'value'})
    except ValidationError as e:
        print(f"   Caught ValidationError: {e}")
        print(f"   Context: {e.context}")
    except DataProcessingError as e:
        print(f"   Caught DataProcessingError: {e}")

    # Demo 4: Direct exception raise
    print("\n4. Context Manager with Cleanup:")
    try:
        with resource_manager("test_resource"):
            print("   Resource in use...")
            raise ValueError("Simulated error")
    except ValueError as e:
        print(f"   Caught: {e} (context manager cleaned up)")

    print("\n" + "=" * 60)
    print("Demo complete - check logs for detailed error information")
    print("=" * 60)


if __name__ == "__main__":
    demonstrate_error_handling()
