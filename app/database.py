import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# -----------------------------
# Pull connection string from environment variable
# -----------------------------
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "SQLALCHEMY_DATABASE_URL",
    "postgresql+psycopg://postgres.fsgeorfboljqcnpchvyj:sanko3217anko@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
)

# -----------------------------
# Create engine
# -----------------------------
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    future=True  # SQLAlchemy 2.0 style
)

# -----------------------------
# Create session
# -----------------------------
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# -----------------------------
# Base class for models
# -----------------------------
Base = declarative_base()

# -----------------------------
# Dependency for FastAPI
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# Optional: quick test if DB is reachable
# -----------------------------
def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1;")
        print("✅ Database connection successful")
    except OperationalError as e:
        print("❌ Database connection failed:", e)

# Run test on import (optional)
test_connection()
