from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.config import get_settings
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
from app.models.user import User
from app.models.program import Program
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead, UserUpdate, PasswordUpdate

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])
settings = get_settings()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
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
    return user


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(db_session)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access = create_access_token(subject=str(user.id))
    refresh = create_refresh_token(subject=str(user.id))
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=60 * 30)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest):
    from app.core.security import decode_token

    try:
        data = decode_token(payload.refresh_token, expected_type="refresh")
        sub = data.get("sub")
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    access = create_access_token(subject=str(sub))
    refresh = create_refresh_token(subject=str(sub))
    return TokenResponse(access_token=access, refresh_token=refresh, expires_in=60 * 30)


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user


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

    base_dir = Path(settings.FILE_STORAGE_DIR) / "avatars"
    base_dir.mkdir(parents=True, exist_ok=True)
    final_name = f"user_{user.id}.{ext}"
    dest_path = base_dir / final_name

    with dest_path.open("wb") as out:
        out.write(content)

    # Store a URL served by the static mount
    user.avatar_url = f"/static/avatars/{final_name}"
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    # Stateless JWTs cannot be revoked without a store. Add Redis denylist later if needed.
    return
