from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from typing import Generator, Optional, cast

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import decode_token
from app.database import get_db
from app.models.user import User, UserRole


_settings = get_settings()
_bearer = HTTPBearer(auto_error=False)


def db_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_current_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    db: Session = Depends(db_session),
) -> User:
    if creds is None or creds.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials, expected_type="access")
        user_id = int(payload.get("sub"))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return cast(User, user)


def get_current_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """Dependency to ensure current user is an admin"""
    if current_user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user


def require_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> None:
    api_key = _settings.API_KEY
    if not api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin operations disabled")
    if x_api_key != api_key:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid API key")
