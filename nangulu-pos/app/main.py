from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from app.database import engine, Base
from app.routers import auth, admin, cashier

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Nangulu POS",
    version="1.0.0"
)

# Add session middleware
app.add_middleware(SessionMiddleware, secret_key="nangulu-secret-key-123456")

# Mount static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(cashier.router, prefix="/api/cashier", tags=["cashier"])

@app.get("/")
def root():
    return {"message": "Nangulu POS API"}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)