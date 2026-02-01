import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# -----------------------------
# Database URL from environment
# -----------------------------
# Make sure in Render you set:
#   SQLALCHEMY_DATABASE_URL=postgresql+psycopg://postgres:sanko3217anko@aws-1-eu-central-1.pooler.supabase.com:5432/postgres
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "SQLALCHEMY_DATABASE_URL",
    "postgresql+psycopg://postgres:defaultpassword@localhost:5432/postgres"
)

# -----------------------------
# Create engine
# -----------------------------
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,  # helps detect stale connections
)

# -----------------------------
# Create session factory
# -----------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -----------------------------
# Base class for models
# -----------------------------
Base = declarative_base()

# -----------------------------
# Dependency for FastAPI routes
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
