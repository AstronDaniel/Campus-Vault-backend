from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.core.config import get_settings


settings = get_settings()
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return _pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return _pwd_context.hash(password)


def _create_token(subject: str, token_type: str, expires_delta: timedelta) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALG)


def create_access_token(subject: str, expires_minutes: Optional[int] = None) -> str:
    minutes = expires_minutes if expires_minutes is not None else settings.ACCESS_TOKEN_EXPIRE_MINUTES
    return _create_token(subject, "access", timedelta(minutes=minutes))


def create_refresh_token(subject: str, expires_days: Optional[int] = None) -> str:
    days = expires_days if expires_days is not None else settings.REFRESH_TOKEN_EXPIRE_DAYS
    return _create_token(subject, "refresh", timedelta(days=days))


def create_password_reset_token(subject: str, expires_minutes: int = 15) -> str:
    return _create_token(subject, "password_reset", timedelta(minutes=expires_minutes))


def decode_token(token: str, expected_type: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALG])
        if payload.get("type") != expected_type:
            raise JWTError("Invalid token type")
        return payload
    except JWTError as e:
        raise e
