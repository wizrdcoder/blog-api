from typing import Optional, Any
from pydantic import PostgresDsn, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "FastAPI PostgreSQL Advanced"

    # Database Configuration
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "fastapi_db"
    DATABASE_URL: Optional[PostgresDsn] = None

    @model_validator(mode="before")
    @classmethod
    def build_database_url(cls, data: dict[str, Any]) -> dict[str, Any]:
        """
        Build DATABASE_URL from components if not provided.
        Using model_validator which runs before field validation.
        """
        # If DATABASE_URL is already provided, return data as-is
        if "DATABASE_URL" in data and data["DATABASE_URL"]:
            return data

        # Extract components from data or use defaults
        username = data.get("POSTGRES_USER", "postgres")
        password = data.get("POSTGRES_PASSWORD", "")
        host = data.get("POSTGRES_SERVER", "localhost")
        port = data.get("POSTGRES_PORT", 5432)
        database = data.get("POSTGRES_DB", "fastapi_db")

        # Build the URL
        if password:
            data["DATABASE_URL"] = (
                f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{database}"
            )
        else:
            data["DATABASE_URL"] = (
                f"postgresql+asyncpg://{username}@{host}:{port}/{database}"
            )

        return data

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # 5 minutes

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60

    # Email
    SMTP_TLS: bool = True
    SMTP_PORT: Optional[int] = None
    SMTP_HOST: Optional[str] = None
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: Optional[str] = None
    EMAILS_FROM_NAME: Optional[str] = None
    ENVIRONMENT: Optional[str] = "development"
    BACKEND_CORS_ORIGINS: list[str] = [
        "localhost:3000",
    ]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    SECRET_KEY: Optional[str] = None
    ALGORITHM: Optional[str] = None

    # Superuser
    # FIRST_SUPERUSER: str = "admin@coder.com"
    # FIRST_SUPERUSER_PASSWORD: str = "password"

    # Logging
    LOG_LEVEL: str = "INFO"

    VERSION: str = "1"

    class Config:
        case_sensitive = True
        env_file = ".env"
        extra = "ignore"


settings = Settings()
