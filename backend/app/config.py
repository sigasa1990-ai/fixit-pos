from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    APP_NAME: str = "FIXIT POS API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    DATABASE_URL: str = "postgresql+asyncpg://fixit:fixit@localhost:5432/fixit_pos"
    DATABASE_ECHO: bool = False
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_HOURS: int = 8
    JWT_REFRESH_EXPIRATION_DAYS: int = 30

    BCRYPT_ROUNDS: int = 10
    PIN_MIN_LENGTH: int = 4
    PIN_MAX_LENGTH: int = 8
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_LOCKOUT_MINUTES: int = 5

    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10

    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "https://pos.fixitsoluciones.com",
        "https://staging-pos.fixitsoluciones.com",
    ]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list[str] = ["*"]
    CORS_ALLOW_HEADERS: list[str] = [
        "Authorization", "Content-Type", "X-Correlation-ID",
        "X-Idempotency-Key", "X-Tenant-ID",
    ]
    CORS_EXPOSE_HEADERS: list[str] = [
        "X-Correlation-ID", "X-Request-ID",
    ]

    BACKBLAZE_B2_KEY_ID: str = ""
    BACKBLAZE_B2_KEY: str = ""
    BACKBLAZE_B2_BUCKET: str = "fixit-pos"

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    settings = Settings()
    if settings.JWT_SECRET_KEY in ("", "change-me-in-production"):
        raise RuntimeError(
            "JWT_SECRET_KEY no configurada. "
            "Establezca una clave secreta segura en la variable de entorno JWT_SECRET_KEY."
        )
    return settings
