from fastapi import Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)


# Dependency for Admin
def get_current_admin(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(User).get(user_id)
    return user


# Dependency for Cashier
def get_current_cashier(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    role = request.session.get("role")
    if not user_id or role != "cashier":
        raise HTTPException(status_code=403, detail="Not authorized")
    user = db.query(User).get(user_id)
    return user
