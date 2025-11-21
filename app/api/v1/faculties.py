from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_api_key
from app.models.faculty import Faculty
from app.schemas.faculty import FacultyCreate, FacultyRead, FacultyUpdate
from app.services.activity_service import ActivityService
from app.models.activity import ActivityType

router = APIRouter(prefix="/api/v1/faculties", tags=["Faculties"])

# Safe fallbacks for missing enum members
SAFE_UPDATED = getattr(ActivityType, "faculty_updated", getattr(ActivityType, "faculty_created", "faculty_updated"))
SAFE_DELETED = getattr(ActivityType, "FACULTY_DELETED", getattr(ActivityType, "faculty_created", "FACULTY_DELETED"))


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
        activity_type=ActivityType.faculty_created,
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
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    data = payload.dict(exclude_unset=True)
    # Validate unique code if changed
    if "code" in data and data["code"] != fac.code:
        if db.query(Faculty).filter(Faculty.code == data["code"], Faculty.id != faculty_id).first():
            raise HTTPException(status_code=400, detail="Faculty code already exists")
        fac.code = data["code"]
    if "name" in data:
        fac.name = data["name"]

    db.add(fac)
    db.commit()
    db.refresh(fac)

    ActivityService.log_activity(
        db=db,
        user_id=1,  # TODO: replace with current user ID
        activity_type=SAFE_UPDATED,
        description=f"Updated faculty: {fac.name}",
        details={"faculty_id": fac.id, "changes": data}
    )

    return fac


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
async def delete_faculty(
    faculty_id: int,
    db: Session = Depends(db_session)
):
    fac = db.get(Faculty, faculty_id)
    if not fac:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Faculty not found")

    # Keep details for audit before deleting
    details = {"faculty_id": fac.id, "faculty_code": fac.code, "faculty_name": fac.name}

    db.delete(fac)
    db.commit()

    ActivityService.log_activity(
        db=db,
        user_id=1,  # TODO: replace with current user ID
        activity_type=SAFE_DELETED,
        description=f"Deleted faculty: {details['faculty_name']}",
        details=details
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)
