from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.deps import db_session, get_current_user
from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
    create_password_reset_token,
    decode_token,
)
from app.models.user import User
from app.models.program import Program
from app.models.resource import Resource
from app.models.resource_bookmark import ResourceBookmark
from app.models.activity import ActivityType
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    TokenResponse,
    PasswordResetRequest,
    PasswordResetConfirm,
)
from app.schemas.user import UserCreate, UserRead, UserUpdate, PasswordUpdate, UserStats
from app.utils.storage import get_storage
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
settings = get_settings()


@router.post(
    "/register", response_model=UserRead, status_code=status.HTTP_201_CREATED
)
def register(payload: UserCreate, db: Session = Depends(db_session)):
    # Check unique email/username
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Validate program exists and belongs to the provided faculty
    program = db.get(Program, payload.program_id)
    if not program:
        raise HTTPException(status_code=400, detail="Program not found")
    if program.faculty_id != payload.faculty_id:
        raise HTTPException(status_code=400, detail="Program does not belong to the specified faculty")

    user = User(
        email=payload.email,
        username=payload.username,
        hashed_password=get_password_hash(payload.password),
        faculty_id=payload.faculty_id,
        program_id=payload.program_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # After successful registration, log the activity
    ActivityService.log_activity(
        db=db,
        user_id=user.id,
        activity_type=ActivityType.user_registered,
        description=f"New user {user.username} registered",
        details={"email": user.email, "faculty_id": user.faculty_id, "program_id": user.program_id}
    )

    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(db_session)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token(subject=str(user.id))
    refresh = create_refresh_token(subject=str(user.id))

    # After successful login, log the activity
    ActivityService.log_activity(
        db=db,
        user_id=user.id,
        activity_type=ActivityType.user_login,
        description=f"User {user.username} logged in",
        details={"email": user.email, "login_time": datetime.utcnow().isoformat()}
    )

    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=60 * 30)


# Mobile-specific login - returns a long-lived token (365 days) so users stay logged in
@router.post("/login/mobile", response_model=TokenResponse)
def login_mobile(payload: LoginRequest, db: Session = Depends(db_session)):
    """
    Mobile-friendly login endpoint that returns a long-lived access token.
    Users stay logged in until they explicitly log out - no token refresh needed.
    Token expires after 1 year of inactivity.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    # Create a long-lived token (365 days = 525600 minutes)
    access = create_access_token(subject=str(user.id), expires_minutes=525600)

    # Log the activity
    ActivityService.log_activity(
        db=db,
        user_id=user.id,
        activity_type=ActivityType.user_login,
        description=f"User {user.username} logged in via mobile",
        details={"email": user.email, "login_time": datetime.utcnow().isoformat(), "platform": "mobile"}
    )

    # expires_in is in seconds (365 days)
    return TokenResponse(access_token=access, refresh_token=None, expires_in=365 * 24 * 60 * 60)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    try:
        data = decode_token(payload.refresh_token, expected_type="refresh")
        sub = data.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access = create_access_token(subject=str(sub))
    refresh = create_refresh_token(subject=str(sub))
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=60 * 30)


@router.post("/password/reset/request", status_code=status.HTTP_204_NO_CONTENT)
def password_reset_request(payload: PasswordResetRequest, db: Session = Depends(db_session)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user:
        # Do not leak whether a user exists
        return
    token = create_password_reset_token(subject=str(user.id), expires_minutes=30)
    reset_link = f"{settings.SERVER_HOST}:{settings.SERVER_PORT}/reset?token={token}"
    # TODO: send email. For now, log it.
    print("Password reset link:", reset_link)
    return


@router.post("/password/reset/validate-token")
def validate_reset_token(payload: dict, db: Session = Depends(db_session)):
    """Validate a password reset token without consuming it"""
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=400, detail="Token is required")
    
    try:
        data = decode_token(token, expected_type="password_reset")
        sub = data.get("sub")
        if sub is None:
            raise ValueError("missing sub")
        user_id = int(sub)
        
        user = db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
            
        return {"valid": True, "email": user.email}
    except Exception:
        return {"valid": False, "expired": True}


@router.post("/password/reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
def password_reset_confirm(payload: PasswordResetConfirm, db: Session = Depends(db_session)):
    try:
        data = decode_token(payload.token, expected_type="password_reset")
        sub = data.get("sub")
        if sub is None:
            raise ValueError("missing sub")
        user_id = int(sub)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password too short")

    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    return


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


@router.get("/me/stats", response_model=UserStats)
def get_user_stats(db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    """Get current user's contribution statistics"""
    from sqlalchemy import func
    
    # Count resources uploaded by user
    total_uploads = db.query(func.count(Resource.id)).filter(Resource.uploader_id == user.id).scalar() or 0
    
    # Sum total downloads across user's resources
    total_downloads = db.query(func.coalesce(func.sum(Resource.download_count), 0)).filter(Resource.uploader_id == user.id).scalar() or 0
    
    # Count user's bookmarks
    total_bookmarks = db.query(func.count(ResourceBookmark.id)).filter(ResourceBookmark.user_id == user.id).scalar() or 0
    
    # Calculate average rating for user's resources
    rating_stats = db.query(
        func.coalesce(func.sum(Resource.rating_sum), 0),
        func.coalesce(func.sum(Resource.rating_count), 0)
    ).filter(Resource.uploader_id == user.id).first()
    
    rating_sum = rating_stats[0] or 0
    rating_count = rating_stats[1] or 0
    average_rating = round(rating_sum / rating_count, 1) if rating_count > 0 else 0.0
    
    # Calculate contribution score (weighted metric)
    # Formula: uploads * 10 + downloads * 1 + (average_rating * rating_count)
    contribution_score = int(total_uploads * 10 + total_downloads + (average_rating * rating_count))
    
    return UserStats(
        total_uploads=total_uploads,
        total_downloads=int(total_downloads),
        total_bookmarks=total_bookmarks,
        contribution_score=contribution_score,
        average_rating=average_rating
    )


@router.get("/me/resources")
def get_my_resources(db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    """Get all resources uploaded by the current user"""
    resources = db.query(Resource).filter(Resource.uploader_id == user.id).order_by(Resource.created_at.desc()).all()
    return resources


@router.patch("/me", response_model=UserRead)
def update_me(payload: UserUpdate, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    # If updating email or username, ensure uniqueness
    if payload.email and payload.email != user.email:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = payload.email

    if payload.username and payload.username != user.username:
        if db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = payload.username

    # Update first_name and last_name if provided
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name

    # If updating faculty/program, validate the mapping
    new_program_id = payload.program_id if payload.program_id is not None else user.program_id
    new_faculty_id = payload.faculty_id if payload.faculty_id is not None else user.faculty_id

    if (payload.program_id is not None) or (payload.faculty_id is not None):
        program = db.get(Program, new_program_id)
        if not program:
            raise HTTPException(status_code=400, detail="Program not found")
        if program.faculty_id != new_faculty_id:
            raise HTTPException(status_code=400, detail="Program does not belong to the specified faculty")
        user.program_id = new_program_id
        user.faculty_id = new_faculty_id

    if payload.avatar_url is not None:
        user.avatar_url = payload.avatar_url

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(payload: PasswordUpdate, db: Session = Depends(db_session), user: User = Depends(get_current_user)):
    if not verify_password(payload.old_password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Old password is incorrect")
    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    return


@router.post("/me/avatar", response_model=UserRead)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    # Validate file type (basic) and size
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed for avatar")

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    # Determine extension
    from pathlib import Path

    allowed_exts = {"jpg", "jpeg", "png"}
    filename = file.filename or "avatar"
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in allowed_exts:
        # try to infer from content-type
        if "jpeg" in content_type:
            ext = "jpg"
        elif "png" in content_type:
            ext = "png"
        else:
            raise HTTPException(status_code=400, detail="Unsupported image type. Use jpg or png")

    # Save via storage backend (Drive or Local)
    storage = get_storage()
    _, public_url = storage.save_avatar(user_id=user.id, filename=file.filename, content_type=content_type, content=content)

    user.avatar_url = public_url
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/me/banner", response_model=UserRead)
async def upload_banner(
    file: UploadFile = File(...),
    db: Session = Depends(db_session),
    user: User = Depends(get_current_user),
):
    """Upload profile banner/cover image"""
    # Validate file type (basic) and size
    content_type = (file.content_type or "").lower()
    if not content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image uploads are allowed for banner")

    content = await file.read()
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(status_code=400, detail="File too large")

    # Determine extension
    from pathlib import Path

    allowed_exts = {"jpg", "jpeg", "png"}
    filename = file.filename or "banner"
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in allowed_exts:
        # try to infer from content-type
        if "jpeg" in content_type:
            ext = "jpg"
        elif "png" in content_type:
            ext = "png"
        else:
            raise HTTPException(status_code=400, detail="Unsupported image type. Use jpg or png")

    # Save via storage backend (Drive or Local) - use banner subfolder
    storage = get_storage()
    # Create a banner-specific filename
    banner_filename = f"banner_{user.id}.{ext}"
    _, public_url = storage.save_avatar(user_id=user.id, filename=banner_filename, content_type=content_type, content=content)

    user.banner_url = public_url
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(db_session)
):
    # Log logout activity
    ActivityService.log_activity(
        db=db,
        user_id=current_user.id,
        activity_type=ActivityType.user_logout,
        description=f"User {current_user.username} logged out",
        details={"logout_time": datetime.utcnow().isoformat()}
    )

    return {"message": "Successfully logged out"}
