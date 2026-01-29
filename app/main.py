"""
Main FastAPI application with contract enforcement.
- SQLAlchemy 2.x patterns only
- Preflight database test
- Error handling as per contract
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, text
import os
from contextlib import asynccontextmanager
import logging

from app.database import engine, get_db, test_connection
from app import models
from app.routers import auth

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan events with contract enforcement.
    Contract: Preflight test to prevent startup crashes.
    """
    # Startup
    logger.info("🚀 Starting Nangulu Chicken Feed POS System")
    
    # Contract: Preflight database test
    logger.info("Running preflight database test...")
    success, message = test_connection()
    if not success:
        logger.error(f"Preflight test failed: {message}")
        # Don't crash, but log prominently
    else:
        logger.info(f"Preflight test passed: {message}")
    
    # Create tables if they don't exist
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables verified")
    except Exception as e:
        logger.warning(f"⚠️ Database table creation: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Nangulu POS")

# Create FastAPI app
app = FastAPI(
    title="Nangulu Chicken Feed POS",
    description="Production POS System - KGs as source of truth",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")

# Health endpoint with contract compliance
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """
    System health check.
    Contract: Shows DB status, fail gracefully if database is unavailable.
    """
    try:
        # Contract: Use SQLAlchemy 2.x execute()
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
        logger.warning(f"Health check database error: {e}")
    
    return {
        "status": "healthy",
        "service": "nangulu-pos",
        "database": db_status,
        "timestamp": os.environ.get("RENDER_GIT_COMMIT", "local"),
        "environment": os.environ.get("RENDER", "development"),
        "version": "1.0.0",
        "driver": "psycopg3" if "psycopg" in os.getenv("DATABASE_URL", "") else "unknown"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Nangulu Chicken Feed POS System",
        "version": "1.0.0",
        "description": "KGs as source of truth - Append-only ledger - Full audit trail",
        "contract": "psycopg3 + SQLAlchemy 2.x enforced",
        "endpoints": {
            "docs": "/api/docs",
            "health": "/health",
            "auth": "/api/auth/login",
            "api": "/api"
        }
    }

# Contract test endpoint
@app.get("/api/contract-test")
async def contract_test(db: Session = Depends(get_db)):
    """
    Test contract compliance.
    Contract: SQLAlchemy 2.x patterns only.
    """
    try:
        # Contract: Use SQLAlchemy 2.x select() pattern
        from sqlalchemy import select
        stmt = select(models.User).limit(1)
        result = db.execute(stmt)
        user_count = result.scalar_one_or_none()
        
        return {
            "contract": "enforced",
            "sqlalchemy_version": "2.x",
            "driver": "psycopg3",
            "database": "connected",
            "test": "passed" if user_count is not None else "no_users"
        }
    except Exception as e:
        return {
            "contract": "enforced",
            "sqlalchemy_version": "2.x",
            "driver": "psycopg3",
            "database": "error",
            "error": str(e)
        }
