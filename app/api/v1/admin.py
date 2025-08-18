from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.api.deps import db_session
from app.core.config import get_settings
from app.models.user import User
from app.models.resource import Resource
from app.models.resource_download import ResourceDownloadEvent

router = APIRouter(prefix="/api/v1/admin", tags=["Admin"])
settings = get_settings()


def _require_api_key(x_api_key: str | None) -> None:
    if not settings.API_KEY or x_api_key != settings.API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")


@router.get("/stats")
def stats(x_api_key: str | None = Header(None, alias="X-API-Key"), db: Session = Depends(db_session)):
    _require_api_key(x_api_key)

    users = db.query(func.count(User.id)).scalar() or 0
    resources = db.query(func.count(Resource.id)).scalar() or 0
    downloads = db.query(func.count(ResourceDownloadEvent.id)).scalar() or 0

    return {
        "users": users,
        "resources": resources,
        "downloads": downloads,
    }


@router.get("/downloads/daily")
def downloads_daily(
    days: int = 7,
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    db: Session = Depends(db_session),
):
    _require_api_key(x_api_key)

    since = datetime.utcnow() - timedelta(days=max(1, min(days, 90)))

    rows = (
        db.query(
            func.date(ResourceDownloadEvent.created_at).label("day"),
            func.count(ResourceDownloadEvent.id),
        )
        .filter(ResourceDownloadEvent.created_at >= since)
        .group_by(func.date(ResourceDownloadEvent.created_at))
        .order_by(func.date(ResourceDownloadEvent.created_at))
        .all()
    )
    return [{"day": str(day), "count": count} for day, count in rows]
