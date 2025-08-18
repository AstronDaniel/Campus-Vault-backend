from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import io
import csv

from app.api.deps import db_session
from app.models.faculty import Faculty
from app.models.program import Program
from app.models.course_unit import CourseUnit

router = APIRouter(prefix="/api/v1/catalog", tags=["Catalog"])


@router.get("/export.json")
def export_json(db: Session = Depends(db_session)):
    faculties = db.query(Faculty).order_by(Faculty.name).all()
    programs = db.query(Program).order_by(Program.name).all()
    course_units = db.query(CourseUnit).order_by(CourseUnit.program_id, CourseUnit.year, CourseUnit.semester, CourseUnit.name).all()

    return {
        "faculties": [
            {"id": f.id, "name": f.name, "code": f.code} for f in faculties
        ],
        "programs": [
            {"id": p.id, "name": p.name, "code": p.code, "faculty_id": p.faculty_id} for p in programs
        ],
        "course_units": [
            {
                "id": c.id,
                "name": c.name,
                "code": c.code,
                "program_id": c.program_id,
                "year": c.year,
                "semester": c.semester,
            }
            for c in course_units
        ],
    }


@router.get("/export.csv")
def export_csv(db: Session = Depends(db_session)):
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["FACULTIES"])  # section header
    writer.writerow(["id", "name", "code"])
    for f in db.query(Faculty).order_by(Faculty.name):
        writer.writerow([f.id, f.name, f.code])
    writer.writerow([])

    writer.writerow(["PROGRAMS"])  # section header
    writer.writerow(["id", "name", "code", "faculty_id"])
    for p in db.query(Program).order_by(Program.name):
        writer.writerow([p.id, p.name, p.code, p.faculty_id])
    writer.writerow([])

    writer.writerow(["COURSE_UNITS"])  # section header
    writer.writerow(["id", "name", "code", "program_id", "year", "semester"])
    for c in db.query(CourseUnit).order_by(CourseUnit.program_id, CourseUnit.year, CourseUnit.semester, CourseUnit.name):
        writer.writerow([c.id, c.name, c.code, c.program_id, c.year, c.semester])

    output.seek(0)
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=campusvault_catalog.csv"
    })
