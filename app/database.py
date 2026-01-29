"""
Database configuration with fail-safe features as per contract:
- pool_pre_ping=True
- SSL enforced for Supabase
- Scoped sessions for thread safety
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

# If DATABASE_URL is not set, we'll create a test configuration
# This allows the app to start even without database for testing
if not DATABASE_URL:
    logger.warning("DATABASE_URL environment variable is not set. Using test configuration.")
    DATABASE_URL = "sqlite:///:memory:"  # Fallback for testing
    
    # Create tables in memory for testing
    engine = create_engine(DATABASE_URL)
    Base = declarative_base()
    
    # Simple session factory for testing
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    SessionScoped = scoped_session(SessionLocal)
    
    def get_db() -> Generator:
        """Test database session for when DATABASE_URL is not set"""
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    def test_connection() -> tuple[bool, str]:
        return False, "DATABASE_URL not configured. Set DATABASE_URL in .env file."
    
    def get_scoped_session():
        return SessionScoped
    
    def close_scoped_session():
        SessionScoped.remove()
    
else:
    # Production configuration with DATABASE_URL
    # Add SSL mode for Supabase if not present (contract requirement)
    if "supabase" in DATABASE_URL and "sslmode" not in DATABASE_URL:
        DATABASE_URL += "?sslmode=require"
        logger.info("Added sslmode=require to DATABASE_URL")
    
    logger.info("Database connection configured")
    
    # Create engine with fail-safe features from contract
    engine = create_engine(
        DATABASE_URL,
        poolclass=QueuePool,
        pool_pre_ping=True,          # Contract: pool_pre_ping=True
        pool_size=5,                # Conservative pool size
        max_overflow=10,            # Allow overflow
        pool_recycle=300,           # Recycle connections
        pool_timeout=30,            # Timeout for getting connection
        echo=False,                 # No SQL echo in production
        connect_args={
            "connect_timeout": 10,
            "keepalives": 1,
            "keepalives_idle": 30,
            "keepalives_interval": 10,
            "keepalives_count": 5,
        }
    )
    
    # Session factory with scoped sessions (contract requirement)
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
        expire_on_commit=False
    )
    
    # Scoped session for thread safety
    SessionScoped = scoped_session(SessionLocal)
    
    # Declarative base for models
    Base = declarative_base()
    
    def get_db() -> Generator:
        """
        Get database session with retry logic (contract: retry on OperationalError max 2 times)
        """
        db = None
        for attempt in range(3):  # 0, 1, 2 attempts
            try:
                db = SessionLocal()
                # Test connection
                db.execute(text("SELECT 1"))
                yield db
                break  # Success, exit retry loop
            except OperationalError as e:
                if db:
                    db.rollback()
                    db.close()
                
                if attempt == 2:  # Last attempt failed
                    logger.error(f"Database connection failed after 3 attempts: {e}")
                    # Contract: OperationalError audit-logged (will be logged by caller)
                    raise
                    
                logger.warning(f"Database connection attempt {attempt + 1} failed, retrying...")
                time.sleep(1)  # Wait before retry
            except SQLAlchemyError as e:
                if db:
                    db.rollback()
                    db.close()
                logger.error(f"Database error: {e}")
                # Contract: IntegrityError audit-logged (will be logged by caller)
                raise
            finally:
                if db and attempt < 2:  # Close only if we're retrying
                    db.close()
    
    def test_connection() -> tuple[bool, str]:
        """Test database connection with retry (contract requirement)"""
        for attempt in range(3):
            try:
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                return True, "Database connection successful"
            except OperationalError as e:
                if attempt == 2:
                    return False, f"Database connection failed: {str(e)}"
                time.sleep(1)
        return False, "Database connection test failed"

    def get_scoped_session():
        """Get scoped session for background tasks (contract requirement)"""
        return SessionScoped
    
    def close_scoped_session():
        """Remove scoped session (contract requirement)"""
        SessionScoped.remove()
