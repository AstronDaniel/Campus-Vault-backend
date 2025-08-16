from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import db_session, require_api_key
from app.models.faculty import Faculty
from app.schemas.faculty import FacultyCreate, FacultyRead

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
def create_faculty(payload: FacultyCreate, db: Session = Depends(db_session)):
    if db.query(Faculty).filter(Faculty.code == payload.code).first():
        raise HTTPException(status_code=400, detail="Faculty code already exists")
    fac = Faculty(name=payload.name, code=payload.code)
    db.add(fac)
    db.commit()
    db.refresh(fac)
    return fac
