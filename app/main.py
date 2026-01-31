from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.routers import auth, admin, cashier
from app.database import Base, engine

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Nangulu POS", version="1.0.0")
app.add_middleware(SessionMiddleware, secret_key="nangulu-secret-key-123456")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Set templates folder
templates = Jinja2Templates(directory="app/static/templates")  # <- updated path

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(cashier.router, prefix="/api/cashier", tags=["cashier"])

# Root login page
@app.get("/")
def root(request: Request):
    # Pop error message from session if it exists
    error = request.session.pop("error", None)
    return templates.TemplateResponse("index.html", {"request": request, "error": error})

@app.get("/health")
def health():
    return {"status": "ok"}
