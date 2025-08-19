from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.api.deps import db_session, get_current_user, require_api_key
from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationCreate, NotificationRead, NotificationBroadcast

router = APIRouter(prefix="/api/v1/notifications", tags=["Notifications"])


@router.get("/", response_model=list[NotificationRead])
def list_notifications(
    only_unread: bool = Query(False),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    q = db.query(Notification).filter(Notification.user_id == user.id)
    if only_unread:
        q = q.filter(Notification.read_at.is_(None))
    return q.order_by(desc(Notification.created_at)).offset(offset).limit(limit).all()


@router.post("/test", response_model=NotificationRead, status_code=status.HTTP_201_CREATED)
def create_test_notification(payload: NotificationCreate, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    n = Notification(user_id=user.id, title=payload.title, body=payload.body)
    db.add(n)
    db.commit()
    db.refresh(n)
    return n


@router.post("/{notification_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(notification_id: int, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    n = db.get(Notification, notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(status_code=404, detail="Notification not found")
    if n.read_at is None:
        n.read_at = datetime.utcnow()
        db.add(n)
        db.commit()
    return


@router.post("/broadcast", response_model=int, dependencies=[Depends(require_api_key)], status_code=status.HTTP_201_CREATED)
def broadcast(payload: NotificationBroadcast, db: Session = Depends(db_session)):
    # naive broadcast to all users
    from app.models.user import User as _User

    users = db.query(_User).all()
    count = 0
    for u in users:
        db.add(Notification(user_id=u.id, title=payload.title, body=payload.body))
        count += 1
    db.commit()
    return count
