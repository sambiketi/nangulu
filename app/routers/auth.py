"""
Authentication router - Step 3 of execution order.
Contract: User management, password hashing, JWT auth.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any, Dict

from app.database import get_db
from app import models
from app.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
    require_admin,
    audit_log_action
)

router = APIRouter(prefix="/auth", tags=["authentication"])

# Response schemas (inline for now, will move to schemas.py)
class TokenResponse:
    def __init__(self, access_token: str, token_type: str, user: Dict[str, Any]):
        self.access_token = access_token
        self.token_type = token_type
        self.user = user

class MessageResponse:
    def __init__(self, message: str):
        self.message = message

@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    OAuth2 compatible token login.
    Contract: JWT auth only via python-jose[cryptography]
    """
    # Find user
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    
    # Validate credentials
    if not user or not verify_password(form_data.password, user.password_hash):
        audit_log_action(
            db=db,
            user_id=user.id if user else None,
            action="LOGIN_FAILED",
            notes=f"Failed login attempt for username: {form_data.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        audit_log_action(
            db=db,
            user_id=user.id,
            action="LOGIN_DENIED_INACTIVE",
            notes=f"Inactive user attempted login: {user.username}"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=access_token_expires
    )
    
    # Audit successful login
    audit_log_action(
        db=db,
        user_id=user.id,
        action="LOGIN_SUCCESS",
        notes=f"User {user.username} logged in successfully"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "full_name": user.full_name,
            "role": user.role,
            "is_active": user.is_active
        }
    }

@router.post("/change-password")
async def change_password(
    current_password: str,
    new_password: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Change password for authenticated user.
    Contract: Cashier can change own password only.
    """
    # Verify current password
    if not verify_password(current_password, current_user.password_hash):
        audit_log_action(
            db=db,
            user_id=current_user.id,
            action="PASSWORD_CHANGE_FAILED",
            notes="Current password incorrect"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Update password
    current_user.password_hash = get_password_hash(new_password)
    db.commit()
    db.refresh(current_user)
    
    # Audit password change
    audit_log_action(
        db=db,
        user_id=current_user.id,
        action="PASSWORD_CHANGE_SUCCESS",
        table_name="users",
        record_id=current_user.id,
        notes="User changed password"
    )
    
    return {"message": "Password updated successfully"}

@router.get("/me")
async def read_users_me(current_user: models.User = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Get current user information.
    """
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None
    }

@router.post("/logout")
async def logout(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Logout user (audit only, JWT tokens are stateless).
    Contract: All actions audit-logged.
    """
    audit_log_action(
        db=db,
        user_id=current_user.id,
        action="LOGOUT",
        notes=f"User {current_user.username} logged out"
    )
    
    return {"message": "Successfully logged out"}

# Admin-only endpoints
@router.post("/create-user")
async def create_user(
    username: str,
    password: str,
    full_name: str,
    role: str = "cashier",
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Create new user (admin only).
    Contract: Admin can create cashier.
    """
    # Validate role
    if role not in ["admin", "cashier"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be 'admin' or 'cashier'"
        )
    
    # Check if username exists
    existing_user = db.query(models.User).filter(models.User.username == username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Create new user
    hashed_password = get_password_hash(password)
    db_user = models.User(
        username=username,
        password_hash=hashed_password,
        full_name=full_name,
        role=role
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Audit user creation
    audit_log_action(
        db=db,
        user_id=current_user.id,
        action="USER_CREATE",
        table_name="users",
        record_id=db_user.id,
        new_values={
            "username": db_user.username,
            "role": db_user.role,
            "full_name": db_user.full_name
        },
        notes=f"Admin {current_user.username} created user {db_user.username}"
    )
    
    return {
        "id": db_user.id,
        "username": db_user.username,
        "full_name": db_user.full_name,
        "role": db_user.role,
        "is_active": db_user.is_active,
        "created_at": db_user.created_at.isoformat() if db_user.created_at else None
    }

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: int,
    is_active: bool,
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Update user active status (admin only).
    Contract: Admin can freeze/unfreeze, disable.
    """
    # Don't allow self-deactivation
    if user_id == current_user.id and not is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate yourself"
        )
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    old_status = user.is_active
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    
    # Audit status change
    audit_log_action(
        db=db,
        user_id=current_user.id,
        action="USER_STATUS_UPDATE",
        table_name="users",
        record_id=user_id,
        old_values={"is_active": old_status},
        new_values={"is_active": is_active},
        notes=f"Admin {current_user.username} updated user {user.username} status to {'active' if is_active else 'inactive'}"
    )
    
    return {
        "id": user.id,
        "username": user.username,
        "is_active": user.is_active,
        "updated_at": user.updated_at.isoformat() if user.updated_at else None
    }

@router.get("/users")
async def list_users(
    current_user: models.User = Depends(require_admin),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    List all users (admin only).
    Contract: Admin can view all users.
    """
    users = db.query(models.User).order_by(models.User.created_at.desc()).all()
    
    return {
        "users": [
            {
                "id": user.id,
                "username": user.username,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
            for user in users
        ],
        "count": len(users)
    }
