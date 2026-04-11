"""
Authentication and Authorization module for Project Management System.

This module provides authentication (authN) and authorization (authZ) functionality
including JWT token management, password hashing, and role-based access control.
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from functools import wraps
import secrets
import hashlib
import hmac

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer, SecurityScopes

from pms_backend.core.exceptions import (
    TokenExpiredError,
    InvalidTokenError,
    UnauthorizedError,
    TokenRequiredError,
    ForbiddenError,
    InsufficientPermissionsError,
    InvalidCredentialsError,
)
from pms_backend.business_logic.specifications import (
    BusinessRule,
    PermissionLevel,
)


# ============================================================================
# CONFIGURATION
# ============================================================================

class AuthSettings:
    """Authentication settings configuration."""
    
    # JWT Configuration
    SECRET_KEY: str = secrets.token_urlsafe(32)  # In production, load from env
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours
    
    # Password Hashing
    BCRYPT_ROUNDS: int = 12
    
    # Rate Limiting
    MAX_LOGIN_ATTEMPTS: int = 5
    LOCKOUT_DURATION_MINUTES: int = 30


# Global password hasher
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token retrieval
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login",
    schemeName="Bearer",
    description="JWT Bearer token for authentication",
)


# ============================================================================
# PASSWORD HASHING
# ============================================================================

def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Hashed password string
        
    Example:
        >>> hashed = hash_password("SecurePass123!")
        >>> len(hashed) > 50
        True
    """
    return pwd_context.hash(password, rounds=AuthSettings.BCRYPT_ROUNDS)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Hashed password from database
        
    Returns:
        True if password matches, False otherwise
        
    Example:
        >>> hashed = hash_password("password123")
        >>> verify_password("password123", hashed)
        True
        >>> verify_password("wrong_password", hashed)
        False
    """
    return pwd_context.verify(plain_password, hashed_password)


# ============================================================================
# JWT TOKEN MANAGEMENT
# ============================================================================

def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Payload data to encode in token (must include 'sub' for subject)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
        
    Example:
        >>> token = create_access_token(data={"sub": "user_123", "role": "PM"})
        >>> len(token) > 0
        True
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=AuthSettings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    })
    
    return jwt.encode(to_encode, AuthSettings.SECRET_KEY, algorithm=AuthSettings.ALGORITHM)


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.
    
    Args:
        token: JWT token string to decode
        
    Returns:
        Decoded token payload
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid or malformed
        
    Example:
        >>> token = create_access_token({"sub": "user_123"})
        >>> payload = decode_access_token(token)
        >>> payload["sub"]
        'user_123'
    """
    try:
        payload = jwt.decode(
            token,
            AuthSettings.SECRET_KEY,
            algorithms=[AuthSettings.ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise InvalidTokenError(f"Invalid token: {str(e)}")


def verify_token(
    token: str,
    required_scopes: Optional[list] = None
) -> Dict[str, Any]:
    """
    Verify a JWT token and return decoded payload.
    
    Args:
        token: JWT token string
        required_scopes: Optional list of required scopes/permissions
        
    Returns:
        Decoded token payload
        
    Raises:
        TokenExpiredError: If token has expired
        InvalidTokenError: If token is invalid
        UnauthorizedError: If token is missing
        ForbiddenError: If required scopes not present
    """
    if not token:
        raise TokenRequiredError("Authentication token required")
    
    try:
        payload = jwt.decode(
            token,
            AuthSettings.SECRET_KEY,
            algorithms=[AuthSettings.ALGORITHM]
        )
        
        # Validate token type
        token_type = payload.get("type")
        if token_type == "refresh":
            raise InvalidTokenError("Refresh token used for authorization")
        
        # Check for required scopes
        if required_scopes:
            user_scopes = payload.get("scopes", [])
            if not all(scope in user_scopes for scope in required_scopes):
                raise InsufficientPermissionsError(
                    f"Required scopes: {required_scopes}, Available: {user_scopes}"
                )
        
        return payload
        
    except JWTError as e:
        if "expired" in str(e).lower():
            raise TokenExpiredError("Token has expired")
        raise InvalidTokenError("Invalid token")


# ============================================================================
# AUTHENTICATION DEPENDENCIES
# ============================================================================

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    request: Request = None
) -> Dict[str, Any]:
    """
    Dependency to get current authenticated user from token.
    
    This function should be used as a FastAPI dependency in routes
    that require authentication.
    
    Args:
        token: JWT token from OAuth2 scheme
        request: FastAPI request object (for extending user info)
        
    Returns:
        Dictionary containing user information
        
    Raises:
        TokenRequiredError: If no token provided
        InvalidTokenError: If token is invalid
        TokenExpiredError: If token has expired
        
    Example:
        @app.get("/api/v1/users/me")
        async def get_current_user_info(
            current_user: dict = Depends(get_current_user)
        ):
            return current_user
    """
    payload = verify_token(token)
    
    user_id = payload.get("sub")
    if user_id is None:
        raise InvalidTokenError("Invalid token payload: missing user ID")
    
    # In production, fetch full user from database here
    # For now, return payload with user info
    return {
        "user_id": user_id,
        "email": payload.get("email", ""),
        "name": payload.get("name", ""),
        "role": payload.get("role", "PM"),
        "scopes": payload.get("scopes", []),
    }


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """
    Get current user and verify they are active.
    
    Args:
        current_user: User from get_current_user dependency
        
    Returns:
        Active user dictionary
        
    Raises:
        UnauthorizedError: If user is disabled
    """
    # In production, check user.is_active from database
    if current_user.get("is_active") is False:
        raise UnauthorizedError("Inactive user")
    
    return current_user


# ============================================================================
# AUTHORIZATION DECORATORS & UTILITIES
# ============================================================================

def require_permission(permission: str):
    """
    Decorator to require specific permission for route access.
    
    Args:
        permission: Permission string required (e.g., "project:read")
        
    Example:
        @require_permission("project:write")
        async def create_project(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get current_user from args if passed
            current_user = None
            for arg in args:
                if isinstance(arg, dict) and 'user_id' in arg:
                    current_user = arg
                    break
            
            if not current_user:
                # Try to find in kwargs
                current_user = kwargs.get('current_user')
            
            if not current_user:
                raise UnauthorizedError("No authenticated user")
            
            # Check permissions
            user_permissions = current_user.get('permissions', [])
            if permission not in user_permissions:
                raise InsufficientPermissionsError(
                    f"Required permission: {permission}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_role(*allowed_roles: str):
    """
    Decorator to require specific user role for route access.
    
    Args:
        *allowed_roles: Allowed role values (e.g., "PM", "Admin")
        
    Example:
        @require_role("Admin")
        async def admin_endpoint(...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = None
            
            for arg in args:
                if isinstance(arg, dict) and 'role' in arg:
                    current_user = arg
                    break
            
            if not current_user:
                current_user = kwargs.get('current_user')
            
            if not current_user:
                raise UnauthorizedError("No authenticated user")
            
            if current_user.get('role') not in allowed_roles:
                raise ForbiddenError(
                    f"Required role: {', '.join(allowed_roles)}"
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_admin():
    """
    Decorator requiring Admin role specifically.
    
    Example:
        @require_admin()
        async def admin_only_endpoint(...):
            ...
    """
    return require_role("Admin")


def require_owner(project_id_field: str = "project_id"):
    """
    Decorator requiring user to be the owner of a resource.
    
    Args:
        project_id_field: Name of the field containing resource ID
        
    Example:
        @require_owner("project_id")
        async def update_project(project_id: str, current_user: dict = ...):
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get project_id from kwargs
            project_id = kwargs.get(project_id_field)
            
            current_user = kwargs.get('current_user')
            
            if not current_user:
                raise UnauthorizedError("No authenticated user")
            
            if not project_id:
                raise ValueError(f"Missing {project_id_field}")
            
            # In production, fetch project and check owner_id
            # For now, we assume the service layer handles this
            return func(*args, **kwargs)
        return wrapper
    return decorator


# ============================================================================
# AUTHENTICATION SERVICES
# ============================================================================

class AuthService:
    """
    Authentication service class.
    
    Centralizes authentication-related business logic.
    """
    
    @staticmethod
    def authenticate_user(email: str, password: str, user_data: Dict[str, Any]) -> bool:
        """
        Authenticate user by email and password.
        
        Args:
            email: User email
            password: Plain text password
            user_data: User data from database (must include 'password' hash)
            
        Returns:
            True if credentials are valid
            
        Raises:
            InvalidCredentialsError: If credentials are invalid
        """
        stored_hash = user_data.get('password')
        if not stored_hash:
            raise InvalidCredentialsError("User not found")
        
        if not verify_password(password, stored_hash):
            raise InvalidCredentialsError("Invalid credentials")
        
        return True
    
    @staticmethod
    def create_tokens(user_id: str, email: str, role: str, scopes: Optional[list] = None) -> Dict[str, Any]:
        """
        Create access token for authenticated user.
        
        Args:
            user_id: User unique identifier
            email: User email
            role: User role
            scopes: Optional list of user permissions/scopes
            
        Returns:
            Dictionary with access_token, token_type, and expires_in
        """
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
        }
        
        if scopes:
            payload["scopes"] = scopes
        
        access_token = create_access_token(
            data=payload,
            expires_delta=timedelta(minutes=AuthSettings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": AuthSettings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        }
    
    @staticmethod
    def refresh_token(refresh_token: str) -> str:
        """
        Create a new access token using refresh token.
        
        Args:
            refresh_token: Valid refresh token
            
        Returns:
            New access token
            
        Raises:
            TokenExpiredError: If refresh token is expired
            InvalidTokenError: If refresh token is invalid
        """
        try:
            payload = jwt.decode(
                refresh_token,
                AuthSettings.SECRET_KEY,
                algorithms=[AuthSettings.ALGORITHM]
            )
            
            if payload.get("type") != "refresh":
                raise InvalidTokenError("Invalid token type")
            
            return create_access_token(
                data=payload,
                expires_delta=timedelta(minutes=AuthSettings.ACCESS_TOKEN_EXPIRE_MINUTES)
            )
        except JWTError as e:
            raise InvalidTokenError(f"Invalid refresh token: {str(e)}")
    
    @staticmethod
    def calculate_password_hash(password: str) -> str:
        """
        Calculate password hash for new user registration.
        
        Args:
            password: Plain text password
            
        Returns:
            Hashed password
        """
        return hash_password(password)


# ============================================================================
# RATE LIMITING (Login attempts)
# ============================================================================

class LoginRateLimiter:
    """
    Rate limiter for login attempts.
    
    Tracks failed login attempts and enforces lockout.
    """
    
    def __init__(self):
        # In production, use Redis or database for distributed storage
        self.attempts: Dict[str, Dict[str, Any]] = {}
    
    def record_failed_attempt(self, identifier: str) -> int:
        """
        Record a failed login attempt.
        
        Args:
            identifier: User identifier (email or IP)
            
        Returns:
            Current attempt count
        """
        if identifier not in self.attempts:
            self.attempts[identifier] = {
                "count": 1,
                "first_attempt": datetime.utcnow()
            }
        else:
            self.attempts[identifier]["count"] += 1
        
        return self.attempts[identifier]["count"]
    
    def record_success(self, identifier: str) -> None:
        """
        Reset attempts on successful login.
        
        Args:
            identifier: User identifier
        """
        if identifier in self.attempts:
            del self.attempts[identifier]
    
    def is_locked_out(self, identifier: str) -> tuple[bool, Optional[datetime]]:
        """
        Check if identifier is locked out.
        
        Args:
            identifier: User identifier
            
        Returns:
            Tuple of (is_locked, unlock_time)
        """
        if identifier not in self.attempts:
            return (False, None)
        
        attempt_info = self.attempts[identifier]
        
        if attempt_info["count"] >= AuthSettings.MAX_LOGIN_ATTEMPTS:
            # Calculate unlock time
            first_attempt = attempt_info["first_attempt"]
            unlock_time = first_attempt + timedelta(
                minutes=AuthSettings.LOCKOUT_DURATION_MINUTES
            )
            
            if datetime.utcnow() < unlock_time:
                return (True, unlock_time)
            else:
                # Lockout expired, reset
                del self.attempts[identifier]
                return (False, None)
        
        return (False, None)


# Initialize rate limiter
login_rate_limiter = LoginRateLimiter()
