from fastapi import FastAPI, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy.orm import Session

from app.routers import auth, admin, cashier
from app.database import Base, engine, get_db

# -----------------------------
# Create all tables if not exist
# -----------------------------
Base.metadata.create_all(bind=engine)

# -----------------------------
# Initialize FastAPI app
# -----------------------------
app = FastAPI(title="Nangulu POS", version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key="nangulu-secret-key-123456")  # simple session

# -----------------------------
# Mount static files
# -----------------------------
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# -----------------------------
# Templates
# -----------------------------
templates = Jinja2Templates(directory="app/static/templates")  # must match template folder

# -----------------------------
# Include routers
# -----------------------------
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(cashier.router, prefix="/api/cashier", tags=["cashier"])

# -----------------------------
# Root login page
# -----------------------------
@app.get("/")
def root(request: Request):
    """
    Root login page
    """
    # Pop error message from session if it exists
    error = request.session.pop("error", None)
    return templates.TemplateResponse("index.html", {"request": request, "error": error})

# -----------------------------
# Health check
# -----------------------------
@app.get("/health")
def health():
    return {"status": "ok"}

# -----------------------------
# DB connection check
# -----------------------------
@app.get("/db-check")
def db_check(db: Session = Depends(get_db)):
    """
    Verify that FastAPI can connect to the database.
    Returns counts from key tables if successful.
    """
    try:
        users_count = db.execute("SELECT COUNT(*) FROM users").scalar()
        inventory_count = db.execute("SELECT COUNT(*) FROM inventory_items").scalar()
        sales_count = db.execute("SELECT COUNT(*) FROM sales").scalar()

        return {
            "status": "ok",
            "db_connected": True,
            "users_count": users_count,
            "inventory_count": inventory_count,
            "sales_count": sales_count
        }
    except Exception as e:
        return {
            "status": "error",
            "db_connected": False,
            "error": str(e)
        }
