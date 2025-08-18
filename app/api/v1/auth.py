from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, get_current_user
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
from app.models.user import User
from app.models.program import Program
from app.schemas.auth import LoginRequest, RefreshRequest, TokenResponse
from app.schemas.user import UserCreate, UserRead

router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(db_session)):
    # Check unique email/username
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    if db.query(User).filter(User.username == payload.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    # Validate program exists and belongs to the provided faculty
    program = db.query(Program).get(payload.program_id)
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


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout():
    # Stateless JWTs cannot be revoked without a store. Add Redis denylist later if needed.
    return
