from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# -----------------------------
# Password utilities
# -----------------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check a plain password against a hashed password"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt"""
    return pwd_context.hash(password)


# -----------------------------
# Generic user dependency
# -----------------------------
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """Return the currently logged-in user based on session"""
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or not role:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return user


# -----------------------------
# Role-specific dependencies
# -----------------------------
def get_current_admin(user: User = Depends(get_current_user)) -> User:
    """Return admin user"""
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


def get_current_cashier(user: User = Depends(get_current_user)) -> User:
    """Return cashier user"""
    if user.role != "cashier":
        raise HTTPException(status_code=403, detail="Cashier access required")
    return user
