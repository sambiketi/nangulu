"""
Authentication and security module following contract:
- JWT auth only via python-jose[cryptography]
- Password hashing only via passlib[bcrypt]
- Role-based access control (Admin/Cashier)
- Server-side input validation
- Full audit trail
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
import os
import logging

from app.database import get_db
from app import models

logger = logging.getLogger(__name__)

# Contract: Password hashing only via passlib[bcrypt]
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Contract: JWT auth only via python-jose[cryptography]
security = HTTPBearer()

# Get configuration from environment
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    """Hash a password (contract: only via passlib[bcrypt])"""
    return pwd_context.hash(password)

def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and verify JWT token"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> models.User:
    """
    Get current authenticated user from JWT token.
    Contract: Server-side role checks.
    """
    token = credentials.credentials
    payload = decode_access_token(token)
    
    if payload is None:
        logger.warning("Invalid JWT token provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    username: str = payload.get("sub")
    if username is None:
        logger.warning("JWT token missing 'sub' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(models.User).filter(models.User.username == username).first()
    if user is None:
        logger.warning(f"User not found: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        logger.warning(f"Inactive user attempted login: {username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inactive user",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def require_admin(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Require admin role.
    Contract: Role-based access control.
    """
    if current_user.role != "admin":
        logger.warning(f"Non-admin user attempted admin action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return current_user

def require_cashier(current_user: models.User = Depends(get_current_user)) -> models.User:
    """
    Require cashier role.
    Contract: Role-based access control.
    """
    if current_user.role != "cashier":
        logger.warning(f"Non-cashier user attempted cashier action: {current_user.username}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cashier privileges required"
        )
    return current_user

def audit_log_action(
    db: Session,
    user_id: int,
    action: str,
    table_name: Optional[str] = None,
    record_id: Optional[int] = None,
    old_values: Optional[Dict] = None,
    new_values: Optional[Dict] = None,
    notes: Optional[str] = None
):
    """
    Create audit log entry.
    Contract: All critical actions audit-logged.
    """
    try:
        audit_entry = models.AuditLog(
            user_id=user_id,
            action=action,
            table_name=table_name,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            notes=notes
        )
        db.add(audit_entry)
        db.commit()
        logger.info(f"Audit log created: {action} by user {user_id}")
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        db.rollback()
        # Don't raise, audit failure shouldn't break main operation
