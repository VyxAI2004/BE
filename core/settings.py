import os
from typing import Optional

class Settings:
    """Application settings loaded from environment variables"""
    
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/dbname")
    
    # JWT
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "your-secret-key-here")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Admin Secret Key for promoting users to admin/super_admin
    ADMIN_SECRET_KEY: str = os.getenv("ADMIN_SECRET_KEY", "")
    
    # First Super Admin credentials (for seeding)
    FIRST_SUPERADMIN_EMAIL: str = os.getenv("FIRST_SUPERADMIN_EMAIL", "superadmin@example.com")
    FIRST_SUPERADMIN_PASSWORD: str = os.getenv("FIRST_SUPERADMIN_PASSWORD", "1")
    FIRST_SUPERADMIN_USERNAME: str = os.getenv("FIRST_SUPERADMIN_USERNAME", "superadmin")
    FIRST_SUPERADMIN_FULLNAME: str = os.getenv("FIRST_SUPERADMIN_FULLNAME", "Super Administrator")
    
    # App Environment
    APP_ENV: str = os.getenv("APP_ENV", "dev")

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    REDIS_PASSWORD: Optional[str] = os.getenv("REDIS_PASSWORD", None)
    
    @classmethod
    def validate_admin_secret_key(cls, key: str) -> bool:
        """Validate admin secret key"""
        if not cls.ADMIN_SECRET_KEY:
            return False
        return key == cls.ADMIN_SECRET_KEY

settings = Settings()
