from fastapi import APIRouter, Form, Request, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy.orm import Session
from starlette.status import HTTP_302_FOUND

from app.database import get_db
from app.models import User
from app.schemas import UserLogin
from app.dependencies import get_password_hash, verify_password

router = APIRouter()

# -----------------------------
# Login endpoint (POST form)
# -----------------------------
@router.post("/login")
def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    role: str = Form(...),
    db: Session = Depends(get_db)
):
    # Find user by username and role
    user = db.query(User).filter(User.username == username, User.role == role).first()
    if not user:
        return JSONResponse({"detail": "User not found"}, status_code=400)

    if not verify_password(password, user.password_hash):
        return JSONResponse({"detail": "Incorrect password"}, status_code=400)

    if not user.is_active:
        return JSONResponse({"detail": "User is inactive"}, status_code=403)

    # Store user id and role in session
    request.session['user_id'] = user.id
    request.session['role'] = user.role

    # Redirect based on role
    if user.role == "admin":
        return RedirectResponse("/api/admin/dashboard", status_code=HTTP_302_FOUND)
    else:
        return RedirectResponse("/api/cashier/dashboard", status_code=HTTP_302_FOUND)


# -----------------------------
# Logout endpoint
# -----------------------------
@router.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=HTTP_302_FOUND)


# -----------------------------
# Optional: API login (JSON)
# -----------------------------
@router.post("/api-login")
def api_login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        return JSONResponse({"detail": "Invalid credentials"}, status_code=400)
    if not user.is_active:
        return JSONResponse({"detail": "User inactive"}, status_code=403)
    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role
    }
