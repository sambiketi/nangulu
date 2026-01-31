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
    # Clear previous errors
    request.session.pop("error", None)

    # 1️⃣ Get user by username only
    user = db.query(User).filter(User.username == username).first()
    if not user:
        request.session["error"] = "User not found"
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    # 2️⃣ Verify role matches the DB
    if user.role != role:
        request.session["error"] = f"Selected role '{role}' does not match user role"
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    # 3️⃣ Verify password
    if not verify_password(password, user.password_hash):
        request.session["error"] = "Incorrect password"
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    # 4️⃣ Check if active
    if not user.is_active:
        request.session["error"] = "User is inactive"
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    # 5️⃣ Store user id and role in session
    request.session['user_id'] = user.id
    request.session['role'] = user.role

    # 6️⃣ Redirect based on role
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
    # Get user by username only
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        return JSONResponse({"detail": "Invalid credentials"}, status_code=400)

    # Optional: validate role if sent in payload (can add if needed)
    # if data.role and user.role != data.role:
    #     return JSONResponse({"detail": "Role does not match user"}, status_code=400)

    if not user.is_active:
        return JSONResponse({"detail": "User inactive"}, status_code=403)

    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role
    }
