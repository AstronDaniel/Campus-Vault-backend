from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_api_key
from app.models.course_unit import CourseUnit
from app.schemas.course_unit import CourseUnitCreate, CourseUnitRead

router = APIRouter(prefix="/api/v1/course-units", tags=["Course Units"])


@router.get("/", response_model=list[CourseUnitRead])
def list_course_units(
    program_id: int | None = None,
    year: int | None = None,
    semester: int | None = None,
    db: Session = Depends(db_session),
):
    q = db.query(CourseUnit)
    if program_id is not None:
        q = q.filter(CourseUnit.program_id == program_id)
    if year is not None:
        q = q.filter(CourseUnit.year == year)
    if semester is not None:
        q = q.filter(CourseUnit.semester == semester)
    return q.order_by(CourseUnit.program_id, CourseUnit.year, CourseUnit.semester, CourseUnit.name).all()


@router.get("/{course_unit_id}", response_model=CourseUnitRead)
def get_course_unit(course_unit_id: int, db: Session = Depends(db_session)):
    obj = db.get(CourseUnit, course_unit_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course unit not found")
    return obj


@router.post("/", response_model=CourseUnitRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
def create_course_unit(payload: CourseUnitCreate, db: Session = Depends(db_session)):
    obj = CourseUnit(
        program_id=payload.program_id,
        name=payload.name,
        code=payload.code,
        year=payload.year,
        semester=payload.semester,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj
