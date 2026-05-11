import os
import secrets
import base64
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # JWT
    JWT_SECRET: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_HOURS: int = 24

    # Encryption for API keys (independent from JWT_SECRET)
    ENCRYPTION_KEY: str = ""

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/agenthub.db"

    # CORS
    CORS_ORIGINS: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"

    # Environment
    ENVIRONMENT: str = "development"
    ENABLE_HTTPS: bool = False

    # Hermes instance config
    HERMES_DATA_ROOT: str = "./data/hermes"
    HOST_DATA_ROOT: str = ""  # Host-side path for Docker volume mounts
    PORT_RANGE_START: int = 9001
    PORT_RANGE_END: int = 9100

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def model_post_init(self, __context):
        # Read from Docker secrets if available
        self._read_docker_secrets()

        # JWT_SECRET validation
        if not self.JWT_SECRET:
            if self.ENVIRONMENT == "production":
                raise ValueError("生产环境必须设置 JWT_SECRET")
            # Development: generate temporary key
            self.JWT_SECRET = secrets.token_urlsafe(32)
        elif self.JWT_SECRET == "change-me-in-production-use-random-32-chars":
            raise ValueError("检测到使用默认 JWT_SECRET，禁止在生产环境使用")

        if len(self.JWT_SECRET) < 32:
            raise ValueError("JWT_SECRET 长度不少于32字符")

        # ENCRYPTION_KEY validation (independent from JWT_SECRET)
        if not self.ENCRYPTION_KEY:
            if self.ENVIRONMENT == "production":
                raise ValueError("生产环境必须设置独立的 ENCRYPTION_KEY")
            # Development: generate temporary key
            key_bytes = secrets.token_bytes(32)
            self.ENCRYPTION_KEY = base64.urlsafe_b64encode(key_bytes).decode()

        if len(self.ENCRYPTION_KEY) < 32:
            raise ValueError("ENCRYPTION_KEY 长度不少于32字符")

        # CORS validation
        if self.ENVIRONMENT == "production":
            if not self.CORS_ORIGINS or "*" in self.CORS_ORIGINS:
                raise ValueError(
                    "生产环境必须指定明确的 CORS 域名（逗号分隔），不能使用通配符"
                )

    def _read_docker_secrets(self):
        """Read secrets from Docker secrets files if available."""
        secrets_dir = Path("/run/secrets")

        if secrets_dir.exists():
            # JWT_SECRET from file
            jwt_secret_file = secrets_dir / "jwt_secret"
            if jwt_secret_file.exists():
                self.JWT_SECRET = jwt_secret_file.read_text().strip()

            # ENCRYPTION_KEY from file
            encryption_key_file = secrets_dir / "encryption_key"
            if encryption_key_file.exists():
                self.ENCRYPTION_KEY = encryption_key_file.read_text().strip()


@lru_cache
def get_settings() -> Settings:
    return Settings()
