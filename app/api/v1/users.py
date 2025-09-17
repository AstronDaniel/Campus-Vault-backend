from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pathlib import Path

from app.api.deps import db_session, require_api_key
from app.core.config import get_settings
from app.core.security import get_password_hash
from app.models.user import User
from app.models.program import Program
from app.schemas.user import UserRead, UserUpdate, AdminPasswordReset, UsersBulkDeleteRequest, UsersBulkDeleteResponse, AdminVerifyUserRequest, UserCreate

router = APIRouter(prefix="/api/v1/users", tags=["Users"])
settings = get_settings()


@router.get("/", response_model=list[UserRead], dependencies=[Depends(require_api_key)])
def list_users(db: Session = Depends(db_session)):
    return db.query(User).order_by(User.created_at.desc()).all()


@router.get("/{user_id}", response_model=UserRead, dependencies=[Depends(require_api_key)])
def get_user(user_id: int, db: Session = Depends(db_session)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead, dependencies=[Depends(require_api_key)])
def admin_update_user(user_id: int, payload: UserUpdate, db: Session = Depends(db_session)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # email/username uniqueness
    if payload.email and payload.email != user.email:
        if db.query(User).filter(User.email == payload.email).first():
            raise HTTPException(status_code=400, detail="Email already registered")
        user.email = payload.email

    if payload.username and payload.username != user.username:
        if db.query(User).filter(User.username == payload.username).first():
            raise HTTPException(status_code=400, detail="Username already taken")
        user.username = payload.username

    # faculty/program validation
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

    # --- FIX: allow admin to update role ---
    # Accept role in request body if present (for admin use)
    role = getattr(payload, "role", None)
    if role is not None:
        user.role = role

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/{user_id}/password", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
def admin_reset_password(user_id: int, payload: AdminPasswordReset, db: Session = Depends(db_session)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.hashed_password = get_password_hash(payload.new_password)
    db.add(user)
    db.commit()
    return


@router.patch("/{user_id}/verify", response_model=UserRead, dependencies=[Depends(require_api_key)])
def admin_verify_user(user_id: int, payload: AdminVerifyUserRequest, db: Session = Depends(db_session)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_verified = payload.is_verified
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/bulk", response_model=UsersBulkDeleteResponse, dependencies=[Depends(require_api_key)])
def bulk_delete_users(payload: UsersBulkDeleteRequest, db: Session = Depends(db_session)):
    deleted = 0
    not_found: list[int] = []

    for uid in payload.ids:
        user = db.get(User, uid)
        if not user:
            not_found.append(uid)
            continue

        # Remove avatar if exists
        avatar = getattr(user, "avatar_url", None)
        if avatar:
            prefix = "/static/"
            if avatar.startswith(prefix):
                rel_path = avatar[len(prefix):]
                abs_path = Path(settings.FILE_STORAGE_DIR) / rel_path
                try:
                    abs_path.unlink(missing_ok=True)
                except Exception:
                    pass
            else:
                # Remote (Drive)
                pass

        db.delete(user)
        deleted += 1

    db.commit()
    return UsersBulkDeleteResponse(deleted=deleted, not_found=not_found)


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
def admin_create_user(payload: UserCreate, db: Session = Depends(db_session)):
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


@router.delete("/{user_id}", response_model=dict, status_code=status.HTTP_200_OK, dependencies=[Depends(require_api_key)])
def delete_user(user_id: int, db: Session = Depends(db_session)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Remove avatar if exists
    avatar = getattr(user, "avatar_url", None)
    if avatar:
        prefix = "/static/"
        if avatar.startswith(prefix):
            rel_path = avatar[len(prefix):]  # e.g. avatars/user_1.jpg
            abs_path = Path(settings.FILE_STORAGE_DIR) / rel_path
            try:
                abs_path.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            # Remote (Drive)
            pass

    db.delete(user)
    db.commit()
    return {"message": "User deleted successfully"}
