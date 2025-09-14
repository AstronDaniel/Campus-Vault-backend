from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_api_key
from app.models.faculty import Faculty
from app.schemas.faculty import FacultyCreate, FacultyRead, FacultyUpdate
from app.services.activity_service import ActivityService
from app.models.activity import ActivityType

router = APIRouter(prefix="/api/v1/faculties", tags=["Faculties"])


@router.get("/", response_model=list[FacultyRead])
def list_faculties(db: Session = Depends(db_session)):
    return db.query(Faculty).order_by(Faculty.name).all()


@router.get("/{faculty_id}", response_model=FacultyRead)
def get_faculty(faculty_id: int, db: Session = Depends(db_session)):
    fac = db.get(Faculty, faculty_id)
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")
    return fac


@router.post("/", response_model=FacultyRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
async def create_faculty(
    payload: FacultyCreate,
    db: Session = Depends(db_session)
):
    if db.query(Faculty).filter(Faculty.code == payload.code).first():
        raise HTTPException(status_code=400, detail="Faculty code already exists")
    fac = Faculty(name=payload.name, code=payload.code)
    db.add(fac)
    db.commit()
    db.refresh(fac)

    # After successful creation, log the activity
    ActivityService.log_activity(
        db=db,
        user_id=1,  # This should be the current user's ID
        activity_type=ActivityType.FACULTY_CREATED,
        description=f"Created faculty: {fac.name}",
        details={"faculty_id": fac.id, "faculty_code": fac.code}
    )

    return fac


@router.patch("/{faculty_id}", response_model=FacultyRead, dependencies=[Depends(require_api_key)])
async def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    db: Session = Depends(db_session)
):
    fac = db.get(Faculty, faculty_id)
    if not fac:
        raise HTTPException(status_code=404, detail="Faculty not found")

    if payload.code and payload.code != fac.code:
        if db.query(Faculty).filter(Faculty.code == payload.code).first():
            raise HTTPException(status_code=400, detail="Faculty code already exists")
        fac.code = payload.code
    if payload.name is not None:
        fac.name = payload.name

    db.add(fac)
    db.commit()
    db.refresh(fac)

    # After successful update, log the activity
    ActivityService.log_activity(
        db=db,
        user_id=1,  # This should be the current user's ID
        activity_type=ActivityType.FACULTY_UPDATED,
        description=f"Updated faculty: {fac.name}",
        details={"faculty_id": faculty_id}
    )

    return fac


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
def delete_faculty(faculty_id: int, db: Session = Depends(db_session)):
    fac = db.get(Faculty, faculty_id)
    if not fac:
        raise HTTPException(status_code=404, detail="Faculty not found")
    db.delete(fac)
    db.commit()
    return
