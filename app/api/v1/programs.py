from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_api_key
from app.models.program import Program
from app.models.course_unit import CourseUnit
from app.models.faculty import Faculty
from app.schemas.program import ProgramCreate, ProgramRead, ProgramUpdate
from app.schemas.course_unit import CourseUnitRead

router = APIRouter(prefix="/api/v1/programs", tags=["Programs"])


@router.get("/", response_model=list[ProgramRead])
def list_programs(faculty_id: int | None = None, db: Session = Depends(db_session)):
    q = db.query(Program)
    if faculty_id is not None:
        q = q.filter(Program.faculty_id == faculty_id)
    return q.order_by(Program.name).all()


@router.get("/{program_id}", response_model=ProgramRead)
def get_program(program_id: int, db: Session = Depends(db_session)):
    obj = db.get(Program, program_id)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return obj


@router.get("/{program_id}/course-units", response_model=list[CourseUnitRead])
def list_program_course_units(
    program_id: int,
    year: int | None = None,
    semester: int | None = None,
    db: Session = Depends(db_session),
):
    q = db.query(CourseUnit).filter(CourseUnit.program_id == program_id)
    if year is not None:
        q = q.filter(CourseUnit.year == year)
    if semester is not None:
        q = q.filter(CourseUnit.semester == semester)
    return q.order_by(CourseUnit.year, CourseUnit.semester, CourseUnit.name).all()


@router.post("/", response_model=ProgramRead, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_api_key)])
def create_program(payload: ProgramCreate, db: Session = Depends(db_session)):
    if db.query(Program).filter(Program.code == payload.code).first():
        raise HTTPException(status_code=400, detail="Program code already exists")
    obj = Program(faculty_id=payload.faculty_id, name=payload.name, code=payload.code)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{program_id}", response_model=ProgramRead, dependencies=[Depends(require_api_key)])
def update_program(program_id: int, payload: ProgramUpdate, db: Session = Depends(db_session)):
    obj = db.get(Program, program_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Program not found")

    if payload.code and payload.code != obj.code:
        if db.query(Program).filter(Program.code == payload.code).first():
            raise HTTPException(status_code=400, detail="Program code already exists")
        obj.code = payload.code

    if payload.faculty_id is not None:
        if not db.get(Faculty, payload.faculty_id):
            raise HTTPException(status_code=400, detail="Faculty not found")
        obj.faculty_id = payload.faculty_id

    if payload.name is not None:
        obj.name = payload.name

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_api_key)])
def delete_program(program_id: int, db: Session = Depends(db_session)):
    obj = db.get(Program, program_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Program not found")
    db.delete(obj)
    db.commit()
    return
