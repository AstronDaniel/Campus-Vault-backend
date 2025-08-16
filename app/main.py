from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import auth as auth_router
from app.api.v1 import faculties as faculties_router
from app.api.v1 import programs as programs_router
from app.api.v1 import course_units as course_units_router
from app.core.config import get_settings
from app.database import Base, engine
import app.models # Import all models to ensure they are registered with SQLAlchemy


settings = get_settings()

app = FastAPI(title="CampusVault API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router.router)
app.include_router(faculties_router.router)
app.include_router(programs_router.router)
app.include_router(course_units_router.router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.on_event("startup")
def on_startup():
    # Temporary: auto-create tables for initial bring-up. Use Alembic later.
    Base.metadata.create_all(bind=engine)
