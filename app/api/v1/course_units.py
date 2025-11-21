from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_api_key
from app.models.course_unit import CourseUnit
from app.models.program import Program
from app.schemas.course_unit import CourseUnitCreate, CourseUnitRead, CourseUnitUpdate

router = APIRouter(prefix="/api/v1/course-units", tags=["Course Units"])


@router.get("", response_model=list[CourseUnitRead])
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


@router.post("", response_model=CourseUnitRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
def create_course_unit(payload: CourseUnitCreate, db: Session = Depends(db_session)):
    # Optional: enforce unique (program_id, code) pair
    exists = (
        db.query(CourseUnit)
        .filter(CourseUnit.program_id == payload.program_id, CourseUnit.code == payload.code)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Course unit code already exists in this program")

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


@router.patch("/{course_unit_id}", response_model=CourseUnitRead, dependencies=[Depends(require_api_key)])
def update_course_unit(course_unit_id: int, payload: CourseUnitUpdate, db: Session = Depends(db_session)):
    obj = db.get(CourseUnit, course_unit_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Course unit not found")

    # Handle possible program change and code uniqueness check within program
    new_program_id = payload.program_id if payload.program_id is not None else obj.program_id
    new_code = payload.code if payload.code is not None else obj.code

    if payload.program_id is not None:
        if not db.get(Program, payload.program_id):
            raise HTTPException(status_code=400, detail="Program not found")

    # If either program_id or code changes, ensure (program_id, code) uniqueness
    if (new_program_id != obj.program_id) or (new_code != obj.code):
        conflict = (
            db.query(CourseUnit)
            .filter(CourseUnit.program_id == new_program_id, CourseUnit.code == new_code, CourseUnit.id != obj.id)
            .first()
        )
        if conflict:
            raise HTTPException(status_code=400, detail="Course unit code already exists in this program")

    if payload.name is not None:
        obj.name = payload.name
    if payload.code is not None:
        obj.code = payload.code
    if payload.program_id is not None:
        obj.program_id = payload.program_id
    if payload.year is not None:
        obj.year = payload.year
    if payload.semester is not None:
        obj.semester = payload.semester

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{course_unit_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
def delete_course_unit(course_unit_id: int, db: Session = Depends(db_session)):
    obj = db.get(CourseUnit, course_unit_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Course unit not found")
    db.delete(obj)
    db.commit()
    return
