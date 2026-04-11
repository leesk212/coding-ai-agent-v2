# Comprehensive Python Error Handling Best Practices

## Table of Contents
1. [try/except Patterns](#1-tryexcept-patterns)
2. [Custom Exception Hierarchies](#2-custom-exception-hierarchies)
3. [Context Managers](#3-context-managers)
4. [Retry Logic](#4-retry-logic)
5. [Logging Best Practices](#5-logging-best-practices)
6. [Anti-patterns to Avoid](#6-anti-patterns-to-avoid)
7. [References](#references)

---

## 1. try/except Patterns

### 1.1 Proper Use of try/except

The `try/except` construct is Python's primary mechanism for handling exceptions. The key principle is to **catch only what you can handle** and let other exceptions propagate.

```python
# GOOD: Catch specific exceptions you can handle
def read_config_file(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except FileNotFoundError:
        # Handle specific case: file doesn't exist
        print(f"Warning: {filename} not found, using defaults")
        return {"default": "config"}
    except PermissionError:
        # Handle specific case: no read permission
        raise RuntimeError(f"Cannot read {filename}: permission denied")
    except IOError as e:
        # Handle other I/O errors (e.g., network drives)
        print(f"I/O error reading {filename}: {e}")
        return None

# BAD: Catching too broadly without clear intent
def bad_read_config(filename):
    try:
        with open(filename, 'r') as f:
            return f.read()
    except Exception:  # Too broad! Catches everything including KeyboardInterrupt
        print("Error reading file")
        return None
```

**Key Principles:**
- Catch specific exceptions when you know how to handle them
- Only catch broad exceptions when you need to do cleanup or logging
- Always document why you're catching a particular exception
- Consider using `else` clause for code that should only run if no exception occurs

```python
# Using else clause for code that should only run if no exception
def safe_divide(a, b):
    try:
        result = 1 / b
    except ZeroDivisionError:
        return None
    else:
        # Only executes if no exception occurred
        print(f"Division successful: {a} / {b} = {result}")
        return result * a

# Using finally for cleanup that must happen
def process_file(filename):
    file_handle = None
    try:
        file_handle = open(filename, 'r')
        data = file_handle.read()
        return data
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None
    finally:
        # Always executes, even if exception occurred or return happened
        if file_handle:
            file_handle.close()
```

### 1.2 Specific vs Broad Exceptions

Python has a hierarchy of exceptions. Always prefer catching specific exceptions over broad ones.

```python
import builtins

# Check exception hierarchy
print(issubclass(ValueError, Exception))  # True
print(issubclass(TypeError, Exception))   # True
print(issubclass(KeyError, LookupError))  # True

# GOOD: Multiple specific exception handlers
def parse_number(text):
    try:
        return int(text)
    except ValueError:
        print(f"Cannot convert '{text}' to integer")
        return None

# GOOD: Catch related exceptions together with tuple
def read_config_value(config, key, default=None):
    try:
        return config[key]
    except (KeyError, TypeError) as e:
        print(f"Error accessing config: {e}")
        return default

# BAD: Using Exception when more specific exception exists
def divide_numbers(a, b):
    try:
        return a / b
    except Exception as e:  # Would catch KeyboardInterrupt, SystemExit, etc.
        return None

# BETTER: Catch only the specific exception
def divide_numbers(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None
    except TypeError:
        return None
```

### 1.3 Bare Excepts

Bare `except:` clauses are strongly discouraged as they catch **all** exceptions including system-exiting ones like `KeyboardInterrupt` and `SystemExit`.

```python
# BAD: Bare except - catches everything including system exceptions
def bad_exception_handler():
    try:
        risky_operation()
    except:  # NEVER DO THIS
        print("Something went wrong")

# BAD: except Exception without re-raising or proper handling
def also_bad_exception_handler():
    try:
        risky_operation()
    except Exception:  # Catches all exceptions except SystemExit, KeyboardInterrupt
        pass  # Silent failure - extremely dangerous

# BETTER: If you must catch all, explicitly check and re-raise system exceptions
def acceptable_broad_handler():
    try:
        risky_operation()
    except (SystemExit, KeyboardInterrupt):
        raise  # Re-raise system exceptions
    except Exception as e:
        print(f"Unexpected error: {e}")
        # Log the error appropriately
```

### 1.4 Exception Chaining

Python 3 supports explicit exception chaining, which helps preserve the original traceback for debugging.

```python
# Automatic exception chaining (Python 3+)
def parse_user_data(user_input):
    try:
        data = int(user_input)  # Might raise ValueError
    except ValueError as e:
        # Python automatically chains exceptions with __cause__ = None
        raise RuntimeError("Failed to parse user input") from e

# Explicit exception chaining with 'from'
def load_config_file(config_path):
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise ConfigError(f"Configuration file not found: {config_path}") from None
    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in config file: {config_path}") from e

# Suppressing exception chaining with 'from None'
def convert_to_int(value):
    try:
        return int(value)
    except (ValueError, TypeError):
        raise ValueError(f"Cannot convert {value!r} to integer") from None
        # Use 'from None' when the original exception isn't helpful

# Inspecting exception chains
def inspect_exception_chain():
    try:
        try:
            1 / 0
        except ZeroDivisionError:
            raise ValueError("Division failed")
    except ValueError as e:
        print(f"Exception: {e}")
        print(f"__cause__: {e.__cause__}")
        print(f"__context__: {e.__context__}")
        if e.__cause__:
            print(f"Original exception: {e.__cause__}")
```

### 1.5 Best Practice Patterns

```python
# Pattern 1: Try-Except-Else-Finally
def robust_file_operation(filename):
    file = None
    try:
        file = open(filename, 'r')
        data = file.read()
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None
    except PermissionError:
        print(f"No permission to read {filename}")
        return None
    else:
        # Runs only if no exception occurred
        print("File read successfully")
        return data
    finally:
        # Always runs
        if file:
            file.close()

# Pattern 2: Context Manager (preferred over try-finally for resources)
def context_manager_file_operation(filename):
    try:
        with open(filename, 'r') as file:
            data = file.read()
            return data
    except FileNotFoundError:
        print(f"File {filename} not found")
        return None
    # File automatically closed by context manager

# Pattern 3: Reraising with context
def network_request(url):
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        # Log and re-raise with context
        print(f"Request to {url} timed out")
        raise
    except requests.HTTPError as e:
        # Augment exception with more context
        raise ConnectionError(f"HTTP error for {url}: {e}") from e
```

**References:**
- Python Documentation: [Exception Handling](https://docs.python.org/3/tutorial/errors.html#exception-handling)
- Python Documentation: [Errors and Exceptions](https://docs.python.org/3/reference/executionmodel.html#exception-handling)

---

## 2. Custom Exception Hierarchies

### 2.1 When to Create Custom Exceptions

Create custom exceptions when:
- You need to distinguish application-specific error conditions
- You want to provide more context about the error
- You need to handle different error types differently
- You're building a library that should have a clear error API

```python
# When NOT to use custom exceptions (use built-ins instead)
def parse_user_id(user_input):
    if not user_input.isdigit():
        raise ValueError("User ID must be numeric")  # Use built-in
    return int(user_input)

# When TO use custom exceptions
class UserError(Exception):
    """Base exception for user-related errors"""
    pass

class UserNotFoundError(UserError):
    """Raised when a user is not found"""
    pass

class UserInvalidError(UserError):
    """Raised when user data is invalid"""
    pass

class UserAlreadyExistsError(UserError):
    """Raised when trying to create a duplicate user"""
    pass

def get_user(user_id):
    """Retrieve user by ID"""
    # In production, this would query a database
    if user_id not in database:
        raise UserNotFoundError(f"User with ID {user_id} not found")
    
    user = database[user_id]
    if not user.is_valid:
        raise UserInvalidError(f"User {user_id} has invalid data")
    
    return user
```

### 2.2 Naming Conventions

- Always end exception names with "Error"
- Make the name descriptive of what went wrong
- Use clear hierarchies that reflect the domain

```python
# GOOD: Clear, descriptive naming
class PaymentError(Exception):
    """Base exception for payment processing errors"""
    pass

class PaymentValidationError(PaymentError):
    """Raised when payment data is invalid"""
    pass

class PaymentProcessingError(PaymentError):
    """Raised when payment processing fails"""
    pass

class PaymentGatewayError(PaymentProcessingError):
    """Raised when there's an error with the payment gateway"""
    pass

class PaymentTimeoutError(PaymentGatewayError):
    """Raised when payment gateway doesn't respond in time"""
    pass

class PaymentDeclinedError(PaymentProcessingError):
    """Raised when payment is declined by gateway"""
    pass

# BAD: Unclear or misleading names
class PaymentException(Exception):  # Should be "Error"
    pass

class Bad(PaymentError):  # Too vague
    pass

class PaymentErrorThatOccurred(PaymentError):  # Too verbose
    pass
```

### 2.3 Exception Hierarchies and Inheritance

```python
class AppError(Exception):
    """Base exception for all application errors"""
    def __init__(self, message, error_code=None, context=None):
        super().__init__(message)
        self.error_code = error_code
        self.context = context or {}
        self.timestamp = None
    
    def __str__(self):
        msg = super().__str__()
        if self.error_code:
            msg = f"[{self.error_code}] {msg}"
        return msg

class DatabaseError(AppError):
    """Base exception for database operations"""
    pass

class ConnectionError(DatabaseError):
    """Database connection failed"""
    pass

class QueryError(DatabaseError):
    """Database query failed"""
    pass

class ConstraintError(QueryError):
    """Database constraint violation"""
    pass

class ValidationError(QueryError):
    """Data validation failed"""
    pass

# Usage
def save_user(user_data):
    try:
        # Simulated database operation
        if not user_data.get('email'):
            raise ValidationError("Email is required", error_code="USR001")
        
        if not user_data.get('name'):
            raise ValidationError("Name is required", error_code="USR002")
        
        # Insert into database
        cursor = get_db_connection()
        cursor.execute("INSERT INTO users VALUES (...)", user_data)
        cursor.commit()
        
    except ConnectionError as e:
        # Retry logic or fallback
        print(f"Database connection failed: {e}")
        raise
    except ValidationError as e:
        # Return to client for correction
        return {"error": "validation", "details": str(e)}
    except ConstraintError as e:
        # Handle constraint violations
        if "unique" in str(e).lower():
            return {"error": "duplicate", "details": str(e)}
        raise
```

### 2.4 Exception with Additional Context

```python
class APIError(Exception):
    """Base exception for API-related errors"""
    
    def __init__(self, message, status_code=None, response_data=None, headers=None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data
        self.headers = headers or {}
    
    def to_dict(self):
        """Serialize error for API response"""
        result = {"error": str(self)}
        if self.status_code:
            result["status_code"] = self.status_code
        if self.response_data:
            result["details"] = self.response_data
        return result

class RateLimitError(APIError):
    """Raised when API rate limit is exceeded"""
    def __init__(self, message, retry_after, response_data=None):
        super().__init__(
            message, 
            status_code=429,
            response_data=response_data,
            headers={"Retry-After": str(retry_after)}
        )
        self.retry_after = retry_after

class AuthenticationError(APIError):
    """Raised when authentication fails"""
    def __init__(self, message, error_type="authentication_error", error_description=None):
        super().__init__(
            message,
            status_code=401,
            response_data={
                "error": error_type,
                "error_description": error_description
            }
        )

# Usage in API
def create_resource(api_client, resource_data):
    try:
        response = api_client.post("/resources", json=resource_data)
        response.raise_for_status()
        return response.json()
    except requests.HTTPError as e:
        if e.response.status_code == 429:
            retry_after = int(e.response.headers.get("Retry-After", 60))
            raise RateLimitError(
                "API rate limit exceeded",
                retry_after=retry_after,
                response_data=e.response.json()
            )
        elif e.response.status_code == 401:
            raise AuthenticationError(
                "Authentication failed",
                error_type="invalid_token",
                error_description=e.response.json().get("error_description")
            )
        raise APIError(
            f"API request failed: {e}",
            status_code=e.response.status_code,
            response_data=e.response.json()
        )
```

### 2.5 Context Managers with Custom Exceptions

```python
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class TransactionError(Exception):
    """Base exception for transaction errors"""
    pass

class TransactionRollbackError(TransactionError):
    """Raised when transaction rollback fails"""
    pass

class TransactionTimeoutError(TransactionError):
    """Raised when transaction times out"""
    pass

@contextmanager
def database_transaction(db_connection, timeout=30):
    """Context manager for database transactions with error handling"""
    transaction_started = False
    try:
        db_connection.begin()
        transaction_started = True
        logger.info("Transaction started")
        yield db_connection
        if not db_connection.committed:
            db_connection.commit()
            transaction_started = False  # Committed, not rolled back
    except Exception as e:
        if transaction_started:
            try:
                db_connection.rollback()
                logger.warning(f"Transaction rolled back: {e}")
            except Exception as rollback_error:
                raise TransactionRollbackError(
                    f"Failed to rollback transaction: {rollback_error}"
                ) from e
        raise
    finally:
        if transaction_started:
            db_connection.end()
            logger.info("Transaction completed")

# Usage
def transfer_funds(from_account, to_account, amount):
    with database_transaction(connection) as db:
        # Check balance
        balance = db.query("SELECT balance FROM accounts WHERE id = ?", from_account)
        if balance < amount:
            raise TransactionError("Insufficient funds")
        
        # Deduct from source
        db.execute("UPDATE accounts SET balance = balance - ? WHERE id = ?", amount, from_account)
        
        # Add to destination
        db.execute("UPDATE accounts SET balance = balance + ? WHERE id = ?", amount, to_account)
        
        # Record transaction
        db.execute("INSERT INTO transactions ...", from_account, to_account, amount)
```

**References:**
- Python Documentation: [Exception Hierarchy](https://docs.python.org/3/library/exceptions.html)
- Python Best Practices: [PEP 8 Style Guide](https://peps.python.org/pep-0008/#constructors-and-factory-functions)
- Real Python: [Python Exception Handling](https://realpython.com/python-exceptions/)

---

## 3. Context Managers

### 3.1 The `with` Statement for Resource Management

Context managers ensure resources are properly acquired and released, even when exceptions occur.

```python
# Built-in context managers
# File handling
with open('data.txt', 'r') as f:
    content = f.read()
# File is automatically closed even if an exception occurs

# Multiple context managers
with open('input.txt', 'r') as infile, open('output.txt', 'w') as outfile:
    for line in infile:
        outfile.write(line.upper())

# Contextlib built-in context managers
from contextlib import closing, contextmanager, suppress, redirect_stdout, nested

# closing() - for objects without 'with' support
import socket
with closing(socket.socket()) as sock:
    sock.connect(('example.com', 80))
    sock.send(b'GET / HTTP/1.0\r\n\r\n')

# suppress() - temporarily suppress specific exceptions
with suppress(PermissionError, FileNotFoundError):
    os.remove('temp_file.txt')
# Continues execution even if file doesn't exist or permission denied

# redirect_stdout() - capture stdout
from io import StringIO
output = StringIO()
with redirect_stdout(output):
    print("This goes to output")
    print("Also captured")
print(output.getvalue())
```

### 3.2 Creating Custom Context Managers

There are two ways to create context managers:
1. Using classes (implementing `__enter__` and `__exit__`)
2. Using `@contextmanager` decorator with generators

#### Class-Based Context Manager

```python
class Timer:
    """Context manager for timing code blocks"""
    
    def __init__(self, description="Code block"):
        self.description = description
        self.start_time = None
        self.end_time = None
    
    def __enter__(self):
        import time
        self.start_time = time.time()
        print(f"Starting: {self.description}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        import time
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time
        print(f"Completed: {self.description} in {elapsed:.4f} seconds")
        
        # Return False to propagate exceptions, True to suppress them
        return False

# Usage
with Timer("Database query"):
    # Simulate long-running operation
    import time
    time.sleep(1)

# Accessing timer values after context
with Timer("Memory check") as timer:
    pass
print(f"Duration: {timer.end_time - timer.start_time:.4f}s")
```

#### Using `@contextmanager` Decorator

```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def transaction(db):
    """Context manager for database transactions"""
    try:
        db.begin()
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise

@contextmanager
def temp_directory(name="temp"):
    """Create and clean up a temporary directory"""
    import tempfile
    import shutil
    
    temp_path = tempfile.mkdtemp(prefix=f"{name}_")
    try:
        yield temp_path
    finally:
        shutil.rmtree(temp_path)

# Usage
with transaction(connection) as db:
    db.execute("INSERT INTO logs VALUES ...")
    db.execute("UPDATE users SET status = 'active' WHERE id = ?", user_id)

with temp_directory("backup") as temp_dir:
    # Work with temp directory
    import os
    filepath = os.path.join(temp_dir, "data.txt")
    with open(filepath, 'w') as f:
        f.write("Temporary data")
    # Directory automatically cleaned up
```

### 3.3 Advanced Context Manager Patterns

#### Conditional Context Managers

```python
from contextlib import contextmanager

@contextmanager
def maybe_open_file(filename, mode='r'):
    """Open file only if it exists, otherwise yield None"""
    import os
    
    if os.path.exists(filename):
        with open(filename, mode) as f:
            yield f
    else:
        yield None

# Usage
with maybe_open_file("config.json") as f:
    if f:
        config = json.load(f)
    else:
        config = get_default_config()

@contextmanager
def if_true(condition, value):
    """Yield value if condition is True, otherwise yield None"""
    if condition:
        yield value
    else:
        yield None

with if_true(True, "value") as result:
    print(result)  # Prints "value"

with if_true(False, "value") as result:
    print(result)  # Prints None
```

#### Resource Pooling with Context Managers

```python
import threading
from contextlib import contextmanager
from queue import Queue

class ResourcePool:
    """Thread-safe resource pool using context manager pattern"""
    
    def __init__(self, factory, max_size=5):
        self.factory = factory
        self.pool = Queue(maxsize=max_size)
        self._lock = threading.Lock()
        
        # Pre-fill pool
        for _ in range(max_size):
            self.pool.put(factory())
    
    @contextmanager
    def acquire(self, timeout=30):
        """Acquire a resource from the pool"""
        resource = self.pool.get(timeout=timeout)
        try:
            yield resource
        finally:
            self.pool.put(resource)

# Example: Database connection pool
class ConnectionPool:
    def __init__(self, connection_factory, max_connections=10):
        self.pool = ResourcePool(connection_factory, max_connections)
    
    @contextmanager
    def get_connection(self, timeout=30):
        with self.pool.acquire(timeout=timeout) as conn:
            yield conn

# Usage
def create_connection():
    # In real scenario, this would create a DB connection
    return Connection()

def process_data():
    with connection_pool.get_connection() as conn:
        conn.execute("SELECT * FROM users")
        return conn.fetchall()
```

#### Context Managers with Parameters

```python
from contextlib import contextmanager
from typing import Optional, Type, TypeVar

T = TypeVar('T')

@contextmanager
def temporary_state(obj: T, attribute: str, new_value) -> Generator[T, None, None]:
    """Temporarily change an object's attribute and restore it"""
    original_value = getattr(obj, attribute)
    try:
        setattr(obj, attribute, new_value)
        yield obj
    finally:
        setattr(obj, attribute, original_value)

class DatabaseConfig:
    def __init__(self):
        self.timeout = 30
        self.max_retries = 3
        self.environment = "production"

config = DatabaseConfig()

with temporary_state(config, "timeout", 60):
    # This code runs with timeout=60
    make_db_request()

# config.timeout is restored to 30
print(config.timeout)  # 30

# Multiple attributes
with temporary_state(config, "environment", "testing"):
    with temporary_state(config, "max_retries", 10):
        run_tests()
```

#### Managing Locks and Semaphores

```python
import threading
from contextlib import contextmanager
from typing import Optional

class ManagedLock:
    """Thread-safe lock with optional timeout"""
    
    def __init__(self, timeout: Optional[float] = None):
        self._lock = threading.Lock()
        self._timeout = timeout
    
    @contextmanager
    def acquire(self, blocking: bool = True):
        acquired = self._lock.acquire(blocking=blocking, timeout=self._timeout)
        if acquired:
            try:
                yield self._lock
            finally:
                self._lock.release()
        else:
            raise TimeoutError("Could not acquire lock within timeout")

# Usage in concurrent code
lock = ManagedLock(timeout=5)

def worker(worker_id):
    try:
        with lock.acquire() as l:
            # Critical section
            print(f"Worker {worker_id} has the lock")
    except TimeoutError:
        print(f"Worker {worker_id} timed out waiting for lock")
```

### 3.4 Nested Context Managers

```python
# Python 3.1+: Multiple context managers with comma
def process_file_with_encryption(input_path, output_path):
    with (
        open(input_path, 'rb') as infile,
        GzipFile(output_path, 'wb') as outfile,
        EncryptedStream(infile) as encrypted,
        DecryptedStream(encrypted) as decrypted
    ):
        for line in decrypted:
            outfile.write(line.upper())

# Before Python 3.1 or with complex nesting
def complex_operation():
    with open('input.txt', 'r') as infile:
        with Timer("Processing") as timer:
            with suppress(UnicodeDecodeError):
                for line in infile:
                    process_line(line)

# Using nested() for older Python versions
from contextlib import nested

def old_style_multiple_contexts():
    with nested(
        open('file1.txt', 'r'),
        open('file2.txt', 'w'),
        Timer("Operation")
    ) as (f1, f2, timer):
        # Process files with timer
        pass
```

**References:**
- Python Documentation: [Context Managers](https://docs.python.org/3/reference/compound_stmts.html#with)
- Python Documentation: [contextlib](https://docs.python.org/3/library/contextlib.html)
- Python Documentation: [__enter__() and __exit__()](https://docs.python.org/3/reference/datamodel.html#object.__enter__)

---

## 4. Retry Logic

### 4.1 Manual Retry Implementation

```python
import time
import random
from typing import Callable, Type, Optional, Tuple

def retry(
    func: Callable,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 1.0,
    logger: Optional[object] = None
) -> Callable:
    """
    Decorator for retrying function calls with exponential backoff.
    
    Args:
        func: Function to retry
        exceptions: Tuple of exception types to catch and retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Random jitter factor (0-1)
        logger: Logger instance for logging retries
    
    Returns:
        Decorated function
    """
    def decorator(*args, **kwargs):
        attempt = 0
        delay = initial_delay
        last_exception = None
        
        while attempt < max_retries:
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                last_exception = e
                attempt += 1
                
                if logger:
                    logger.warning(
                        f"Attempt {attempt}/{max_retries} failed: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                
                if attempt < max_retries:
                    # Calculate jitter
                    jitter_factor = 1 + random.uniform(0, jitter)
                    sleep_time = delay * jitter_factor
                    time.sleep(sleep_time)
                    
                    # Exponential backoff with max cap
                    delay = min(delay * exponential_base, max_delay)
        
        raise last_exception
    
    return decorator

# Usage
@retry(
    exceptions=(ConnectionError, TimeoutError),
    max_retries=5,
    initial_delay=1.0,
    max_delay=30.0,
    exponential_base=2,
    jitter=0.5,
    logger=logger
)
def fetch_data(url):
    import requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()
```

### 4.2 Exponential Backoff with Jitter

```python
import time
import random
import math

def calculate_delay(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: float = 0.5
) -> float:
    """
    Calculate delay with exponential backoff and jitter.
    
    Args:
        attempt: Current attempt number (0-indexed)
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Jitter factor (0.0 to 1.0)
    
    Returns:
        Delay in seconds
    """
    # Calculate exponential delay
    exponential_delay = base_delay * (exponential_base ** attempt)
    
    # Add jitter to prevent thundering herd
    jitter_factor = 1 + random.uniform(-jitter/2, jitter/2)
    delayed_with_jitter = exponential_delay * jitter_factor
    
    # Cap at max_delay
    return min(delayed_with_jitter, max_delay)

# Example: Simulated network request
def make_network_request(endpoint, max_attempts=5):
    for attempt in range(max_attempts):
        try:
            # Simulate network call that might fail
            import random
            if random.random() < 0.7:  # 70% chance of failure
                raise ConnectionError(f"Connection failed on attempt {attempt}")
            return f"Success on attempt {attempt + 1}"
        except ConnectionError as e:
            if attempt < max_attempts - 1:
                delay = calculate_delay(
                    attempt=attempt,
                    base_delay=1.0,
                    max_delay=30.0,
                    exponential_base=2.0,
                    jitter=0.5
                )
                print(f"Retry after {delay:.2f}s: {e}")
                time.sleep(delay)
            else:
                raise

# Test the retry logic
result = make_network_request("/api/data")
print(result)
```

### 4.3 Idempotency Considerations

```python
import uuid
from typing import Optional

class IdempotencyError(Exception):
    """Raised when idempotency check fails"""
    pass

class IdempotencyClient:
    """Client for managing idempotent operations"""
    
    def __init__(self, storage):
        self.storage = storage
        self.request_id = str(uuid.uuid4())
    
    def execute_idempotent(self, operation_id: str, operation: Callable) -> any:
        """
        Execute an idempotent operation.
        
        Args:
            operation_id: Unique identifier for this operation
            operation: The operation to execute
        
        Returns:
            Result of the operation
        
        Raises:
            IdempotencyError: If operation already completed
        """
        # Check if operation already completed
        existing = self.storage.get(operation_id)
        if existing:
            # Return cached result
            print(f"Returning cached result for {operation_id}")
            return existing
        
        # Execute operation
        try:
            result = operation()
            
            # Cache result
            self.storage.set(operation_id, {
                'result': result,
                'timestamp': time.time(),
                'status': 'success'
            })
            
            return result
            
        except Exception as e:
            # Store failure state
            self.storage.set(operation_id, {
                'error': str(e),
                'timestamp': time.time(),
                'status': 'failed'
            })
            raise
    
    @property
    def unique_request_id(self) -> str:
        """Generate unique request ID for idempotency"""
        return f"{self.request_id}-{int(time.time())}"

# Example: Idempotent payment processing
class PaymentProcessor:
    def __init__(self):
        self.storage = InMemoryStorage()
        self.idempotency_client = IdempotencyClient(self.storage)
    
    def process_payment(self, amount: float, payment_id: str) -> dict:
        """Process payment with idempotency guarantee"""
        
        def payment_operation():
            # Actual payment processing
            # This should be idempotent (same input = same output)
            return {
                'transaction_id': str(uuid.uuid4()),
                'amount': amount,
                'status': 'completed',
                'timestamp': time.time()
            }
        
        return self.idempotency_client.execute_idempotent(payment_id, payment_operation)

# Storage implementation
class InMemoryStorage:
    def __init__(self):
        self._data = {}
    
    def get(self, key: str) -> Optional[dict]:
        return self._data.get(key)
    
    def set(self, key: str, value: dict):
        self._data[key] = value

# Usage
processor = PaymentProcessor()

# First call
result1 = processor.process_payment(100.0, "payment-123")
print(f"First call: {result1}")

# Same call again - should return cached result
result2 = processor.process_payment(100.0, "payment-123")
print(f"Second call (should be cached): {result2}")
print(f"Same result: {result1 == result2}")
```

### 4.4 Using Tenacity Library

```python
# Install: pip install tenacity
from tenacity import (
    retry,
    stop_after_attempt,
    stop_after_delay,
    retry_if_exception_type,
    retry_if_result,
    wait_exponential,
    wait_random_exponential,
    retry_if_not_result,
    before_log,
    after_log,
    retry_any
)
import logging

logger = logging.getLogger(__name__)

# Basic retry with stop conditions
@retry(
    stop=stop_after_attempt(5),  # Stop after 5 attempts
    wait=wait_exponential(multiplier=1, min=1, max=30),  # Exponential backoff
    retry=retry_if_exception_type((ConnectionError, TimeoutError))
)
def fetch_with_tenacity(url):
    import requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

# Retry with custom wait strategy
@retry(
    stop=stop_after_delay(60),  # Stop after 60 seconds total
    wait=wait_random_exponential(min=1, max=30),  # Random exponential backoff
    reraise=True  # Re-raise the last exception
)
def fetch_with_random_backoff(url):
    import requests
    response = requests.get(url, timeout=10)
    response.raise_for_status()
    return response.json()

# Retry on result condition
@retry(
    stop=stop_after_attempt(3),
    retry=retry_if_result(lambda result: result is None),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
def get_user_data(user_id):
    # Returns None if user not found or data unavailable
    return fetch_user_from_db(user_id)

# Retry with logging
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=1, max=30),
    retry=retry_if_exception_type(Exception),
    before=before_log(logger, logging.WARNING),
    after=after_log(logger, logging.WARNING)
)
def operation_with_logging():
    # Your operation here
    pass

# Custom retry conditions combined
@retry(
    stop=stop_after_attempt(3) | stop_after_delay(60),  # OR condition
    retry=retry_if_exception_type(Exception) | retry_if_result(lambda x: x is None),  # OR condition
    wait=wait_exponential(multiplier=1, min=1, max=30),
    reraise=True
)
def complex_retry_operation():
    # Complex retry logic
    pass

# Retry with cleanup
from tenacity import RetryError

def operation_with_cleanup():
    resource = acquire_resource()
    try:
        result = resource.process()
        return result
    except RetryError as e:
        # Cleanup on retry exhaustion
        logger.error(f"Operation failed after retries: {e}")
        resource.cleanup()
        raise

# Custom retry decorator with parameters
def make_retryable(
    max_retries=3,
    backoff_factor=2,
    exceptions=(Exception,)
):
    def decorator(func):
        return retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=1, min=backoff_factor, max=60),
            retry=retry_if_exception_type(exceptions)
        )(func)
    return decorator

@make_retryable(max_retries=5, backoff_factor=3, exceptions=(ConnectionError,))
def highly_reliable_operation():
    import requests
    return requests.get("https://api.example.com", timeout=30)
```

**References:**
- Tenacity Documentation: [https://tenacity.readthedocs.io/](https://tenacity.readthedocs.io/)
- AWS Architecture: [Retry Strategies and Backoff](https://aws.amazon.com/blogs/architecture/retry-and-backoff-strategies/)
- Microsoft Azure: [Retry Policy](https://learn.microsoft.com/en-us/azure/architecture/best-practices/retry-service-specific)

---

## 5. Logging Best Practices

### 5.1 Basic Logging Configuration

```python
import logging
import sys
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

# Basic logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        RotatingFileHandler('app.log', maxBytes=10*1024*1024, backupCount=5)
    ]
)

logger = logging.getLogger(__name__)

# Log at different levels
logger.debug("Debug message - detailed information")
logger.info("Info message - general information")
logger.warning("Warning message - potential issue")
logger.error("Error message - operation failed")
logger.critical("Critical message - severe error")

# Conditional logging
if logger.isEnabledFor(logging.DEBUG):
    # Expensive operation only if debug is enabled
    data = compute_expensive_data()
    logger.debug(f"Data: {data}")

# Exception logging
def risky_operation():
    try:
        risky_code()
    except Exception as e:
        # Always log exceptions with full traceback
        logger.exception("Error occurred during risky operation")
        raise
```

### 5.2 Structured Logging

```python
import json
import logging
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """Custom formatter for structured JSON logging"""
    
    def format(self, record):
        log_data = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Add extra fields if present
        if hasattr(record, 'extra_fields'):
            log_data.update(record.extra_fields)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        return json.dumps(log_data)

# Usage
def setup_structured_logging():
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    
    # Create file handler with JSON formatting
    handler = RotatingFileHandler('app.json', maxBytes=10*1024*1024, backupCount=5)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger

logger = setup_structured_logging()

# Log with extra context
logger.info(
    "User login successful",
    extra={
        'extra_fields': {
            'user_id': '12345',
            'username': 'john_doe',
            'ip_address': '192.168.1.100',
            'session_id': 'abc123'
        }
    }
)

# Log with exception context
def process_payment(user_id, amount):
    try:
        # Payment processing logic
        result = payment_gateway.charge(user_id, amount)
        logger.info(
            "Payment processed successfully",
            extra={
                'extra_fields': {
                    'user_id': user_id,
                    'amount': amount,
                    'transaction_id': result['id']
                }
            }
        )
        return result
    except PaymentError as e:
        logger.error(
            "Payment failed",
            extra={
                'extra_fields': {
                    'user_id': user_id,
                    'amount': amount,
                    'error_type': type(e).__name__,
                    'error_message': str(e)
                }
            },
            exc_info=True  # Include traceback
        )
        raise
```

### 5.3 Log Levels and When to Use Them

```python
import logging

logger = logging.getLogger(__name__)

# DEBUG - Detailed information for diagnosing problems
def process_data(data):
    logger.debug(f"Processing data: {data}")
    logger.debug(f"Data type: {type(data)}")
    # Only use in development or when troubleshooting
    pass

# INFO - General application information
def start_server():
    logger.info("Starting application server")
    logger.info(f"Environment: {os.getenv('ENVIRONMENT', 'development')}")
    logger.info(f"Version: {app_version}")

# WARNING - Indication of something unexpected
def handle_config_file(filename):
    if not os.path.exists(filename):
        logger.warning(f"Config file not found: {filename}, using defaults")
        return get_default_config()

def deprecated_feature_used():
    logger.warning(
        "Using deprecated feature: {feature_name}",
        stacklevel=2
    )

# ERROR - Operation failed but application continues
def fetch_external_api(endpoint):
    try:
        response = requests.get(endpoint)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error(f"Failed to fetch from {endpoint}: {e}")
        # Return fallback or default
        return None

# CRITICAL - Severe error, application may not continue
def database_connection_failed():
    logger.critical("Database connection lost")
    try:
        # Attempt recovery
        reconnect_database()
    except Exception as e:
        logger.critical(f"Failed to reconnect database: {e}")
        # Application cannot continue without database
        sys.exit(1)

# Best Practices for Log Levels
# - Don't spam DEBUG in production
# - Use INFO for important lifecycle events
# - Use WARNING when something unusual happened but app continues
# - Use ERROR when something failed but app can recover
# - Use CRITICAL only for true emergencies
```

### 5.4 Common Pitfalls to Avoid

```python
import logging

logger = logging.getLogger(__name__)

# BAD: Logging sensitive information
def user_login(username, password):
    logger.debug(f"User logging in with username: {username}, password: {password}")
    # Password should NEVER be logged!
    
# GOOD: Never log sensitive data
def user_login(username, password):
    logger.debug(f"User attempting login for: {username}")
    # Verify password separately
    if verify_password(username, password):
        logger.info(f"User {username} logged in successfully")

# BAD: Logging exceptions without traceback
def process_request(request):
    try:
        handle_request(request)
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        # Missing: exc_info=True to get full traceback
        return None

# GOOD: Always log full exception context
def process_request(request):
    try:
        handle_request(request)
    except Exception as e:
        logger.error("Error processing request", exc_info=True)
        return None

# BAD: Using print instead of logging
def calculate_total(items):
    total = 0
    for item in items:
        print(f"Processing item: {item}")  # Should use logger
        total += item.price
    return total

# GOOD: Use appropriate logging levels
def calculate_total(items):
    logger.debug(f"Calculating total for {len(items)} items")
    total = 0
    for item in items:
        total += item.price
    logger.debug(f"Total calculated: {total}")
    return total

# BAD: Logging too frequently (spam)
def process_datastream(data_stream):
    for item in data_stream:
        logger.info(f"Processing: {item}")  # Too verbose!
    # Consider sampling or using DEBUG level

# GOOD: Sample logging for high-frequency operations
def process_datastream(data_stream):
    import random
    for item in data_stream:
        logger.debug(f"Processing: {item}")
        if random.random() < 0.01:  # Log 1% of items
            logger.info(f"Sample item: {item}")

# BAD: Using exception as log message format
def fetch_config(config_url):
    try:
        response = requests.get(config_url)
        return response.json()
    except Exception:  # This catches everything!
        logger.error(f"Failed to fetch config: {Exception()}")  # Wrong!
        return None

# GOOD: Catch specific exceptions
def fetch_config(config_url):
    try:
        response = requests.get(config_url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        logger.warning(f"Timeout fetching config from {config_url}")
        return get_default_config()
    except requests.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} fetching config")
        return None

# BAD: Logging inside loops without consideration
def batch_process(items):
    for item in items:
        try:
            process(item)
        except Exception as e:
            logger.error(f"Failed to process item: {e}")
            # Logs one entry per item - could be thousands!

# GOOD: Aggregate errors in loops
def batch_process(items):
    failed_items = []
    for item in items:
        try:
            process(item)
        except Exception as e:
            failed_items.append((item, e))
            # Don't log each one individually
    
    if failed_items:
        logger.error(
            f"Batch processing failed for {len(failed_items)} items",
            extra={'extra_fields': {'failed_count': len(failed_items)}}
        )

# GOOD: Use proper exception handling in loops
def batch_process(items):
    for item in items:
        try:
            process(item)
        except Exception as e:
            logger.error(
                f"Failed to process item {item.id}",
                exc_info=True,
                extra={'extra_fields': {'item_id': item.id}}
            )
```

### 5.5 Best Practices Summary

```python
# Best practices checklist:
# 1. Configure logging at application startup
# 2. Use appropriate log levels
# 3. Always use exc_info=True for exceptions
# 4. Never log sensitive data (passwords, tokens, PII)
# 5. Use structured logging for better analysis
# 6. Implement log rotation for production
# 7. Use contextual information in logs
# 8. Consider log sampling for high-frequency operations
# 9. Don't overuse logging - be selective
# 10. Test your logging configuration

import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging(
    app_name="myapp",
    log_level=logging.INFO,
    log_file=None,
    enable_json=False
):
    """
    Configure logging for the application.
    
    Args:
        app_name: Name of the application for logger
        log_level: Root logging level
        log_file: Optional log file path
        enable_json: Whether to use JSON formatting
    """
    
    class CustomFormatter(logging.Formatter):
        def format(self, record):
            if enable_json:
                import json
                from datetime import datetime
                log_data = {
                    'timestamp': datetime.utcnow().isoformat(),
                    'level': record.levelname,
                    'logger': record.name,
                    'message': record.getMessage(),
                }
                if record.exc_info:
                    log_data['exception'] = self.formatException(record.exc_info)
                return json.dumps(log_data)
            return super().format(record)
    
    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(log_level)
    
    # Create handlers
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(CustomFormatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    logger.addHandler(console_handler)
    
    # File handler for production
    if log_file:
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(CustomFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(file_handler)
    
    return logger

# Usage
logger = setup_logging(
    app_name="payment_service",
    log_level=logging.DEBUG,
    log_file="logs/payment_service.log",
    enable_json=False
)
```

**References:**
- Python Documentation: [Logging How-To](https://docs.python.org/3/howto/logging.html)
- Python Documentation: [logging module](https://docs.python.org/3/library/logging.html)
- Google Cloud: [Logging Best Practices](https://cloud.google.com/logging/docs/best-practices)
- ELK Stack: [Structured Logging](https://www.elastic.co/guide/en/elastic-stack-overview/8.x/log-intake.html)

---

## 6. Anti-patterns to Avoid

### 6.1 Common Mistakes

#### Silent Failures

```python
# BAD: Silently catching and ignoring exceptions
def process_data(data):
    try:
        return data.process()
    except Exception:
        pass  # What went wrong? Hidden!

# BETTER: Log and handle appropriately
def process_data(data):
    try:
        return data.process()
    except Exception as e:
        logger.error(f"Failed to process data: {e}", exc_info=True)
        raise

# BETTER: Handle specific exceptions
def process_data(data):
    try:
        return data.process()
    except ValidationError:
        logger.warning(f"Invalid data format: {data}")
        return None
    except ProcessError as e:
        logger.error(f"Processing error: {e}")
        raise

# BAD: Using try-except for control flow
def find_first_positive(numbers):
    for i, num in enumerate(numbers):
        try:
            return numbers[i] / 0  # Will raise
        except ZeroDivisionError:
            continue
    return None

# BETTER: Use proper control flow
def find_first_positive(numbers):
    for num in numbers:
        if num > 0:
            return num
    return None
```

#### Exception Overuse

```python
# BAD: Using exceptions for normal flow control
def divide(a, b):
    try:
        return a / b
    except ZeroDivisionError:
        return None  # Division by zero is common? Use explicit check

# BETTER: Use explicit checks for expected conditions
def divide(a, b):
    if b == 0:
        return None  # Explicit and clear
    return a / b

# BAD: Over-complicating with too many exceptions
def validate_user_input(data):
    try:
        if not data.get('email'):
            raise ValidationError("Email required")
        if not validate_email(data['email']):
            raise EmailValidationError("Invalid email format")
        if len(data['email']) > 100:
            raise EmailLengthError("Email too long")
        # etc...
    except ValidationError as e:
        return {"error": str(e)}
    except EmailValidationError as e:
        return {"error": str(e)}
    except EmailLengthError as e:
        return {"error": str(e)}
    
# BETTER: Simplified validation
def validate_user_input(data):
    errors = []
    
    if not data.get('email'):
        errors.append("Email is required")
    elif not validate_email(data['email']):
        errors.append("Invalid email format")
    elif len(data['email']) > 100:
        errors.append("Email too long")
    
    if errors:
        return {"errors": errors}
    return {"valid": True}
```

#### Improper Exception Handling

```python
# BAD: Catching all exceptions and doing nothing
def api_call():
    try:
        return requests.get("https://api.example.com")
    except:
        pass  # Silent failure!

# BETTER: Log and re-raise or return error
def api_call():
    try:
        return requests.get("https://api.example.com")
    except requests.RequestException as e:
        logger.error(f"API call failed: {e}")
        return None  # Or raise with context

# BAD: Swallowing important exceptions
def delete_user(user_id):
    try:
        db.execute("DELETE FROM users WHERE id = ?", user_id)
    except Exception as e:
        print(f"Warning: {e}")  # Logging not enough!
        # What if user didn't exist?

# BETTER: Handle specific cases
def delete_user(user_id):
    try:
        result = db.execute("DELETE FROM users WHERE id = ?", user_id)
        if result.rowcount == 0:
            logger.warning(f"User {user_id} not found")
            return False
        return True
    except Exception as e:
        logger.error(f"Failed to delete user {user_id}: {e}", exc_info=True)
        raise

# BAD: Broad exception catching in libraries
def create_user(email, password):
    try:
        # Implementation
        pass
    except Exception:
        raise ValueError("Invalid input")  # Lost original exception context

# BETTER: Preserve exception context
def create_user(email, password):
    try:
        # Implementation
        pass
    except ValidationError as e:
        raise ValueError(f"Invalid input: {e}") from e
    except DatabaseError as e:
        raise RuntimeError("Failed to create user") from e
```

### 6.2 Logging Without Handling

```python
# BAD: Logging without actually handling the error
def process_order(order_id):
    try:
        order = get_order(order_id)
        validate_order(order)
        process_payment(order)
    except Exception as e:
        logger.error(f"Order processing failed: {e}")
        # Error logged but not handled! What happens next?

# BETTER: Log AND handle
def process_order(order_id):
    try:
        order = get_order(order_id)
        validate_order(order)
        process_payment(order)
        return {"success": True, "order_id": order_id}
    except OrderNotFoundError:
        logger.warning(f"Order {order_id} not found")
        return {"success": False, "error": "order_not_found"}
    except PaymentError as e:
        logger.error(f"Payment failed for order {order_id}: {e}")
        return {"success": False, "error": "payment_failed"}
    except Exception as e:
        logger.error(f"Unexpected error processing order {order_id}", exc_info=True)
        return {"success": False, "error": "processing_failed"}

# BAD: Logging in wrong place
def data_pipeline():
    logger.info("Starting pipeline")
    
    for item in data_source:
        try:
            process(item)
            logger.info(f"Processed item: {item}")  # Too verbose!
        except Exception as e:
            logger.error(f"Failed: {e}")  # Not specific enough

# BETTER: Log at appropriate boundaries
def data_pipeline():
    logger.info("Starting data pipeline")
    success_count = 0
    error_count = 0
    
    for item in data_source:
        try:
            process(item)
            success_count += 1
        except Exception as e:
            error_count += 1
            logger.error(
                f"Failed to process item {item.id}",
                exc_info=True,
                extra={'extra_fields': {'item_id': item.id}}
            )
    
    logger.info(
        f"Pipeline completed: {success_count} succeeded, {error_count} failed",
        extra={'extra_fields': {'success_count': success_count, 'error_count': error_count}}
    )
```

### 6.3 Comprehensive Anti-pattern Examples

```python
# Anti-pattern: The "Catch-All" Trap
def risky_operation():
    """
    BAD: Catches everything and pretends it's handled
    """
    try:
        # Some risky operation
        result = dangerous_function()
    except:  # Catches SystemExit, KeyboardInterrupt, etc.!
        print("Operation completed")  # Doesn't matter what happened!
        return "success"

# Anti-pattern: Exception as Control Flow
def get_user_preference(user_id, key, default=None):
    """
    BAD: Uses try-except for flow control
    """
    try:
        return database.get_preference(user_id, key)
    except KeyError:
        return default
    except TypeError:
        return default
    except AttributeError:
        return default
    except ValueError:
        return default

# BETTER: Handle specific cases or use get()
def get_user_preference(user_id, key, default=None):
    """
    GOOD: Use appropriate methods or explicit checks
    """
    user = database.get_user(user_id)
    if user:
        return user.preferences.get(key, default)
    return default

# Anti-pattern: Swallowing Context
def fetch_with_context(url):
    """
    BAD: Loses original exception context
    """
    try:
        response = requests.get(url)
        return response.json()
    except Exception:
        raise Exception("Failed to fetch data")

# BETTER: Preserve exception context
def fetch_with_context(url):
    """
    GOOD: Chain exceptions with 'from'
    """
    try:
        response = requests.get(url)
        return response.json()
    except requests.RequestException as e:
        raise FetchError(f"Failed to fetch {url}") from e

# Anti-pattern: Infinite Retry Loops
def forever_retry():
    """
    BAD: Never gives up
    """
    while True:
        try:
            return make_api_call()
        except Exception as e:
            print(f"Retrying... {e}")

# BETTER: Limit retries with backoff
def retry_with_limits(max_retries=5, backoff=1.0):
    """
    GOOD: Limited retries with exponential backoff
    """
    import time
    import random
    
    for attempt in range(max_retries):
        try:
            return make_api_call()
        except Exception as e:
            if attempt == max_retries - 1:
                logger.error(f"All retries exhausted: {e}")
                raise
            delay = backoff * (2 ** attempt) + random.uniform(0, 1)
            logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.2f}s")
            time.sleep(delay)

# Anti-pattern: Logging Without Purpose
def process_with_logging(data):
    """
    BAD: Logs everything without structure
    """
    logger.debug(f"Data: {data}")
    logger.info(f"Processing data")
    try:
        logger.info(f"Converting {type(data)}")
        result = convert(data)
        logger.info(f"Result: {result}")
    except Exception:
        logger.error(f"Error")
        raise

# BETTER: Structured, purposeful logging
def process_with_logging(data):
    """
    GOOD: Log with context and purpose
    """
    logger.debug(f"Processing {len(data)} items", extra={'extra_fields': {'item_count': len(data)}})
    
    try:
        result = convert(data)
        logger.info(f"Successfully converted {len(result)} items")
        return result
    except ConversionError as e:
        logger.error(f"Conversion failed: {e}", exc_info=True)
        raise
```

**References:**
- Python Enhancement Proposal: [PEP 20 - The Zen of Python](https://peps.python.org/pep-0020/)
- Microsoft: [Exception Handling Guidelines](https://learn.microsoft.com/en-us/dotnet/fundamentals/code-analysis/quality-rules/ca1031)
- Google: [Python Style Guide](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings)

---

## 7. References

### Official Documentation
1. Python Software Foundation. "Exception Handling." Python 3.12 Documentation. https://docs.python.org/3/tutorial/errors.html
2. Python Software Foundation. "Errors and Exceptions." Python 3.12 Documentation. https://docs.python.org/3/reference/executionmodel.html#exception-handling
3. Python Software Foundation. "Logging HOWTO." Python 3.12 Documentation. https://docs.python.org/3/howto/logging.html
4. Python Software Foundation. "The contextlib module." Python 3.12 Documentation. https://docs.python.org/3/library/contextlib.html

### Third-Party Libraries
1. Tenacity: "Retry library for Python." https://tenacity.readthedocs.io/
2. Loguru: "Python logging made (stupidly) simple." https://loguru.readthedocs.io/

### Best Practices Articles
1. Real Python. "Python Exception Handling." https://realpython.com/python-exceptions/
2. Martin Fowler. "Patterns of Exception Handling." https://martinfowler.com/articles/exception-handling.html
3. AWS Architecture Blog. "Retry Strategies and Backoff." https://aws.amazon.com/blogs/architecture/retry-and-backoff-strategies/
4. Microsoft Azure. "Retry Policy Best Practices." https://learn.microsoft.com/en-us/azure/architecture/guide/architecture-patterns/retry

### Standards and Guidelines
1. PEP 8 – Style Guide for Python Code. https://peps.python.org/pep-0008/
2. PEP 484 – Type Hints. https://peps.python.org/pep-0484/
3. Google Python Style Guide. https://google.github.io/styleguide/pyguide.html
4. The Hitchhiker's Guide to Python! https://docs.python-guide.org/

---

*This document is a comprehensive reference for Python error handling best practices. It should be kept updated as Python evolves and new best practices emerge. Contributors should ensure all code examples are tested and references are kept current.*
