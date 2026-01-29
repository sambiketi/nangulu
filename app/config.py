from pydantic_settings import BaseSettings
from typing import List, Optional
from datetime import timedelta

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str
    
    # JWT Authentication
    SECRET_KEY: str = "change-this-in-production-secret-key-12345"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Application
    APP_NAME: str = "Nangulu Chicken Feed POS"
    APP_VERSION: str = "1.0.0"
    
    # CORS
    ALLOWED_ORIGINS: List[str] = ["*"]  # Restrict in production
    
    # Password security
    BCRYPT_ROUNDS: int = 12
    
    # Audit
    AUDIT_LOG_ALL: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()
