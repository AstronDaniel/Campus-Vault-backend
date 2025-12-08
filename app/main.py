from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from fastapi.routing import APIRoute
from fastapi.openapi.utils import get_openapi
from typing import Any, Dict

from app.api.v1 import auth as auth_router
from app.api.v1 import faculties as faculties_router
from app.api.v1 import programs as programs_router
from app.api.v1 import course_units as course_units_router
from app.api.v1 import users as users_router
from app.api.v1 import resources as resources_router
from app.api.v1 import catalog as catalog_router
from app.api.v1 import admin as admin_router
from app.api.v1 import notifications as notifications_router
from app.api.v1 import activities as activities_router
from app.core.config import get_settings
from app.database import Base, engine
import app.models as _models  # noqa: F401  # Ensure models are imported for SQLAlchemy
import app.core.activity_listener  # noqa: F401 # Register activity listeners


settings = get_settings()

app = FastAPI(title="CampusVault API", version="0.1.0")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"Incoming request: {request.method} {request.url}")
    print(f"Headers: {request.headers}")
    try:
        response = await call_next(request)
        print(f"Response status: {response.status_code}")
        return response
    except Exception as e:
        print(f"Request failed: {str(e)}")
        raise

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure storage dir exists and mount static files
Path(settings.FILE_STORAGE_DIR).mkdir(parents=True, exist_ok=True)
app.mount(
    "/static",
    StaticFiles(directory=f"{settings.FILE_STORAGE_DIR}/"),
    name="static",
)

# Routers
app.include_router(auth_router.router)
app.include_router(faculties_router.router)
app.include_router(programs_router.router)
app.include_router(course_units_router.router)
app.include_router(users_router.router)
app.include_router(resources_router.router)
app.include_router(catalog_router.router)
app.include_router(admin_router.router)
app.include_router(notifications_router.router)
app.include_router(activities_router.router)

# Update Swagger title with endpoint count
_base_title = app.title


def _count_operations() -> int:
    count = 0
    for route in app.routes:
        if isinstance(route, APIRoute):
            methods = {m for m in (route.methods or set()) if m not in {"HEAD", "OPTIONS"}}
            count += len(methods)
    return count


def custom_openapi() -> Dict[str, Any]:
    schema = getattr(app, "openapi_schema", None)
    if schema is None:
        schema = get_openapi(
            title=f"{_base_title} · {_count_operations()} endpoints",
            version=getattr(app, "version", "0"),
            routes=app.routes,
            description=None,
        )
        app.openapi_schema = schema
    else:
        # keep title in sync even if schema cached
        info = schema.get("info") or {}
        info["title"] = f"{_base_title} · {_count_operations()} endpoints"
        schema["info"] = info
    return schema


app.openapi = custom_openapi  # type: ignore[assignment]


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/")
async def root():
    return {"message": "Welcome to CampusVault API", "docs": "/docs"}


@app.on_event("startup")
def on_startup():
    # Temporary: auto-create tables for initial bring-up. Use Alembic later.
    # Base.metadata.create_all(bind=engine)
    pass
