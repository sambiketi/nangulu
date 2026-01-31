from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas
from app.dependencies import get_password_hash, verify_password

router = APIRouter()

def authenticate_user(db: Session, username: str, password: str):
    user = db.query(models.User).filter(models.User.username == username).first()
    if not user:
        return False
    if not verify_password(password, user.password_hash):
        return False
    if not user.is_active:
        return False
    return user

@router.post("/login", response_model=schemas.LoginResponse)
async def login(
    request: Request,
    user_data: schemas.UserLogin,
    db: Session = Depends(get_db)
):
    user = authenticate_user(db, user_data.username, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Store in session
    request.session["user_id"] = user.id
    request.session["username"] = user.username
    request.session["role"] = user.role
    request.session["full_name"] = user.full_name
    
    # Determine redirect URL
    if user.role == "admin":
        redirect_url = "/static/templates/admin.html"
    else:
        cashier_number = "cashier1" if user.id % 2 == 1 else "cashier2"
        redirect_url = f"/static/templates/{cashier_number}.html"
    
    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "redirect_to": redirect_url
    }

@router.post("/logout")
async def logout(request: Request):
    request.session.clear()
    return {"message": "Logged out successfully"}