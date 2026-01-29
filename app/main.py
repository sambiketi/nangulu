"""
Main FastAPI application.
Following contract: Simple, transparent, no hidden behavior.
"""
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text
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
    Lifespan events for startup/shutdown.
    Contract: No background jobs, no hidden state.
    """
    # Startup
    logger.info("🚀 Starting Nangulu Chicken Feed POS System")
    
    # Create tables if they don't exist (simplified)
    try:
        models.Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables verified")
    except Exception as e:
        logger.warning(f"⚠️ Database table creation: {e}")
    
    # Test database connection
    success, message = test_connection()
    if success:
        logger.info(f"✅ {message}")
    else:
        logger.warning(f"⚠️ {message}")
    
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

# CORS middleware (simple configuration)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production per contract
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (Step 3: auth & roles implemented)
app.include_router(auth.router, prefix="/api")

# Health endpoint (contract: shows DB status)
@app.get("/health")
async def health_check(db: Session = Depends(get_db)):
    """System health check with database connection test"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    return {
        "status": "healthy",
        "service": "nangulu-pos",
        "database": db_status,
        "timestamp": os.environ.get("RENDER_GIT_COMMIT", "local"),
        "environment": os.environ.get("RENDER", "development"),
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Nangulu Chicken Feed POS System",
        "version": "1.0.0",
        "description": "KGs as source of truth - Append-only ledger - Full audit trail",
        "endpoints": {
            "docs": "/api/docs",
            "health": "/health",
            "auth": "/api/auth/login",
            "api": "/api"
        }
    }

# Simple test endpoint
@app.get("/api/test")
async def test_endpoint():
    return {
        "test": "success",
        "step": "3 - auth & roles implemented",
        "contract": "following README contract strictly"
    }
