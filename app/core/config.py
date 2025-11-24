from functools import lru_cache
from typing import List, Optional
from pathlib import Path

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine .env path robustly (works when running from repo root or app/)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_CANDIDATES = [
    _REPO_ROOT / ".env",
    _REPO_ROOT / ".env.local",
    Path.cwd() / ".env",
    Path.cwd() / ".env.local",
]
for _p in _ENV_CANDIDATES:
    if _p.exists():
        _ENV_FILE = str(_p)
        break
else:
    _ENV_FILE = str(_REPO_ROOT / ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", case_sensitive=False)

    # App
    APP_ENV: str = "development"
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    LOG_LEVEL: str = "INFO"

    # Security
    SECRET_KEY: str
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    API_KEY: Optional[str] = None

    # DB/Cache
    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/0"

    # CORS
    CORS_ORIGINS: List[AnyHttpUrl] | List[str] = []

    # Storage
    DRIVE_PROVIDER: str = "local"  # local|gdrive|onedrive
    FILE_STORAGE_DIR: str = "/tmp" # drive provider is set in production 

    # Google Drive
    GDRIVE_CLIENT_ID: Optional[str] = None
    GDRIVE_CLIENT_SECRET: Optional[str] = None
    GDRIVE_REFRESH_TOKEN: Optional[str] = None
    GDRIVE_SERVICE_ACCOUNT_JSON_PATH: Optional[str] = None
    GDRIVE_SERVICE_ACCOUNT_JSON_CONTENT: Optional[str] = None
    GDRIVE_PARENT_FOLDER_ID: Optional[str] = None
    GDRIVE_PUBLIC_READ: bool = False

    # OneDrive / Microsoft 365
    MS_CLIENT_ID: Optional[str] = None
    MS_CLIENT_SECRET: Optional[str] = None
    MS_TENANT_ID: Optional[str] = None
    MS_REFRESH_TOKEN: Optional[str] = None
    MS_DRIVE_ID: Optional[str] = None
    MS_PARENT_FOLDER_ID: Optional[str] = None

    # Email
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    FROM_EMAIL: str

    # Uploads
    MAX_UPLOAD_SIZE_MB: int = 25
    ALLOWED_FILE_TYPES: str = "pdf,doc,docx,ppt,pptx,txt,jpg,png"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            # allow comma-separated or JSON-like list
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                import json

                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [s.strip() for s in v.split(",") if s.strip()]
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[arg-type]
