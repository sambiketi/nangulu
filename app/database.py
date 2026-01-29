"""
Database configuration enforcing contract:
- psycopg3 driver (postgresql+psycopg://)
- SQLAlchemy 2.x API only (future=True)
- SSL enforced for Supabase (sslmode=require)
- Pool pre-ping enabled
- Scoped sessions
- Retry on OperationalError (max 2 times)
- Fail-fast if DATABASE_URL missing
"""
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, declarative_base, scoped_session
from sqlalchemy.pool import QueuePool
import os
from dotenv import load_dotenv
import logging
from typing import Generator
import time

# Try to load .env, but don't fail if it doesn't exist
try:
    load_dotenv()
except:
    pass  # .env might not exist yet

logger = logging.getLogger(__name__)

# Get database URL from environment (fail-fast as per contract)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.error("DATABASE_URL environment variable is not set")
    raise RuntimeError("DATABASE_URL missing")

# Contract: Enforce psycopg3 driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
    logger.info("Enforced psycopg3 driver in DATABASE_URL")

# Contract: SSL enforcement for Supabase
if "supabase" in DATABASE_URL and "sslmode" not in DATABASE_URL:
    if "?" in DATABASE_URL:
        DATABASE_URL += "&sslmode=require"
    else:
        DATABASE_URL += "?sslmode=require"
    logger.info("Added sslmode=require to DATABASE_URL")

logger.info(f"Database URL configured (driver: {'psycopg3' if 'psycopg' in DATABASE_URL else 'other'})")

# Create engine with contract requirements
engine = create_engine(
    DATABASE_URL,
    future=True,          # Contract: SQLAlchemy 2.x API
    poolclass=QueuePool,
    pool_pre_ping=True,   # Contract: Prevent idle connection errors
    pool_size=5,
    max_overflow=10,
    pool_recycle=300,
    pool_timeout=30,
    echo=False,
    connect_args={
        "connect_timeout": 10,
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    }
)

# Contract: Scoped sessions for thread safety
SessionLocal = scoped_session(
    sessionmaker(
        bind=engine,
        autoflush=False,
        autocommit=False,
        future=True  # SQLAlchemy 2.x session
    )
)

# Declarative base for models
Base = declarative_base()

def test_connection():
    """
    Test database connection with contract enforcement.
    Contract: Preflight test to prevent startup crashes.
    """
    try:
        with engine.connect() as conn:
            # Contract: Use SQLAlchemy 2.x execute()
            conn.execute(text("SELECT 1"))
        return True, "Database connection successful"
    except OperationalError as e:
        logger.error(f"Database connection failed: {e}")
        return False, f"Database connection failed: {e}"
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        return False, f"Database error: {e}"

def get_db() -> Generator:
    """
    Get database session with retry logic.
    Contract: Retry max 2 times on OperationalError.
    """
    db = None
    for attempt in range(3):  # 0, 1, 2 attempts
        try:
            db = SessionLocal()
            # Test connection with SQLAlchemy 2.x API
            db.execute(text("SELECT 1"))
            yield db
            break  # Success, exit retry loop
        except OperationalError as e:
            if db:
                db.rollback()
                db.close()
            
            if attempt == 2:  # Last attempt failed
                logger.error(f"Database connection failed after 3 attempts: {e}")
                # Contract: OperationalError audit-logged
                raise RuntimeError(f"Database connection failed: {e}")
                
            logger.warning(f"Database connection attempt {attempt + 1} failed, retrying...")
            time.sleep(1)  # Wait before retry
        except SQLAlchemyError as e:
            if db:
                db.rollback()
                db.close()
            logger.error(f"Database error: {e}")
            # Contract: IntegrityError audit-logged
            raise
        finally:
            if db and attempt < 2:  # Close only if we're retrying
                db.close()

def get_scoped_session():
    """Get scoped session (contract requirement)"""
    return SessionLocal

def close_scoped_session():
    """Remove scoped session (contract requirement)"""
    SessionLocal.remove()
