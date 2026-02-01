import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

# -----------------------------
# Database URL (from Render env)
# -----------------------------
SQLALCHEMY_DATABASE_URL = os.environ.get(
    "SQLALCHEMY_DATABASE_URL",
    "postgresql+psycopg://postgres.fsgeorfboljqcnpchvyj:sanko3217anko@aws-1-eu-central-1.pooler.supabase.com:5432/postgres"
)

# -----------------------------
# Create engine (SQLAlchemy 2.0)
# -----------------------------
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_pre_ping=True,
    future=True
)

# -----------------------------
# Session factory
# -----------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# -----------------------------
# Base model
# -----------------------------
Base = declarative_base()

# -----------------------------
# FastAPI dependency
# -----------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -----------------------------
# Optional DB connection test
# -----------------------------
def test_connection():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✅ Database connection successful")
    except OperationalError as e:
        print("❌ Database connection failed:", e)

# ⚠️ TEMPORARY: comment out after first successful boot
test_connection()
