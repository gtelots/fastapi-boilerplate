"""Application configuration."""

import os
from typing import Literal
from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.enums import Environment

env = Environment(os.getenv("APP_ENV", Environment.DEVELOPMENT))
env_file = ".env.testing" if env == Environment.TESTING else ".env"


class AppSettings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_prefix="app_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file=env_file,
        extra="allow",
    )

    # Environment
    ENV: Environment = Environment.DEVELOPMENT
    DEBUG: bool = False
    SQLALCHEMY_DEBUG: bool = False
    TESTING: bool = False
    LOG_LEVEL: str = "INFO"

    # CORS
    CORS_ORIGINS: list[str] = []
    ALLOWED_HOSTS: set[str] = {"127.0.0.1:3000", "localhost:3000"}

    # Frontend
    FRONTEND_BASE_URL: str = "http://127.0.0.1:3000"
    FRONTEND_DEFAULT_RETURN_PATH: str = "/"

    # Database
    POSTGRES_USER: str = "app"
    POSTGRES_PWD: str = "app"
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DATABASE: str = "app_development"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_SYNC_POOL_SIZE: int = 1  # Specific pool size for sync connection: since we only use it in OAuth2 router, don't waste resources.
    DATABASE_POOL_RECYCLE_SECONDS: int = 600  # 10 minutes
    DATABASE_COMMAND_TIMEOUT_SECONDS: float = 30.0
    DATABASE_STREAM_YIELD_PER: int = 100

    # Redis
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Sentry
    SENTRY_DSN: str | None = None

    # Logfire
    LOGFIRE_TOKEN: str | None = None
    LOGFIRE_IGNORED_ACTORS: set[str] = {
        "organization_access_token.record_usage",
        "personal_access_token.record_usage",
    }

    # OpenAI
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "o4-mini-2025-04-16"

    # Application behaviours
    API_PAGINATION_MAX_LIMIT: int = 100
    WORKER_MAX_RETRIES: int = 20

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    def get_postgres_dsn(self, driver: Literal["asyncpg", "psycopg2"]) -> str:
        return str(
            PostgresDsn.build(
                scheme=f"postgresql+{driver}",
                username=self.POSTGRES_USER,
                password=self.POSTGRES_PWD,
                host=self.POSTGRES_HOST,
                port=self.POSTGRES_PORT,
                path=self.POSTGRES_DATABASE,
            )
        )

    def is_environment(self, environments: set[Environment]) -> bool:
        return self.ENV in environments

    def is_development(self) -> bool:
        return self.is_environment({Environment.DEVELOPMENT})

    def is_testing(self) -> bool:
        return self.is_environment({Environment.TESTING})

    def is_sandbox(self) -> bool:
        return self.is_environment({Environment.SANDBOX})

    def is_staging(self) -> bool:
        return self.is_environment({Environment.STAGING})

    def is_production(self) -> bool:
        return self.is_environment({Environment.PRODUCTION})

    def generate_frontend_url(self, path: str) -> str:
        return f"{self.FRONTEND_BASE_URL}{path}"

class ImageSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="image_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_file=env_file,
        extra="allow",
    )

    TITLE: str = "FastAPI Boilerplate"
    DESCRIPTION: str = "A production-ready FastAPI boilerplate"
    VERSION: str = "0.1.0"
    SOURCE: str = "https://github.com/gtelots/fastapi-boilerplate"
    DOCUMENTATION: str = "https://github.com/gtelots/fastapi-boilerplate/docs"

app_settings = AppSettings()
image_settings = ImageSettings()
