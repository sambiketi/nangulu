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
# Admin stored in memory
# -----------------------------
ADMIN_USER = {
    "username": "admin",
    "password_hash": get_password_hash("admin123"[:72]),  # truncate to 72 chars for bcrypt
    "role": "admin",
    "is_active": True,
    "full_name": "Super Admin",
    "id": 0  # special in-memory ID
}

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
    # Clear previous error
    request.session.pop("error", None)

    # 1️⃣ Check if admin
    if username == ADMIN_USER["username"] and role == ADMIN_USER["role"]:
        if not verify_password(password, ADMIN_USER["password_hash"]):
            request.session["error"] = "Incorrect password"
            return RedirectResponse("/", status_code=HTTP_302_FOUND)
        # store session
        request.session["user_id"] = ADMIN_USER["id"]
        request.session["role"] = ADMIN_USER["role"]
        return RedirectResponse("/api/admin/dashboard", status_code=HTTP_302_FOUND)

    # 2️⃣ Otherwise, check in DB (cashiers)
    user = db.query(User).filter(User.username == username).first()
    if not user:
        request.session["error"] = "User not found"
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    if user.role != role:
        request.session["error"] = f"Selected role '{role}' does not match user role"
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    if not verify_password(password, user.password_hash):
        request.session["error"] = "Incorrect password"
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    if not user.is_active:
        request.session["error"] = "User is inactive"
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    # store session
    request.session['user_id'] = user.id
    request.session['role'] = user.role

    # redirect based on role
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
    # Admin check
    if data.username == ADMIN_USER["username"] and data.role == ADMIN_USER["role"]:
        if not verify_password(data.password, ADMIN_USER["password_hash"]):
            return JSONResponse({"detail": "Incorrect password"}, status_code=400)
        return {
            "message": "Login successful",
            "user_id": ADMIN_USER["id"],
            "username": ADMIN_USER["username"],
            "full_name": ADMIN_USER["full_name"],
            "role": ADMIN_USER["role"]
        }

    # Cashiers from DB
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.password_hash):
        return JSONResponse({"detail": "Invalid credentials"}, status_code=400)

    if data.role and user.role != data.role:
        return JSONResponse({"detail": "Role does not match user"}, status_code=400)

    if not user.is_active:
        return JSONResponse({"detail": "User inactive"}, status_code=403)

    return {
        "message": "Login successful",
        "user_id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role
    }
