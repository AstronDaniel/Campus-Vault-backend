# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Commands

### Development Setup
```bash
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your database credentials and other settings
```

### Running the Application
```bash
# Start the FastAPI development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Access the API documentation
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)

# Health check endpoint
# http://localhost:8000/health
```

### Database Operations
```bash
# Create database tables (temporary approach - tables are auto-created on startup)
# Note: This project is designed to use Alembic for migrations, but currently uses auto-creation
python -c "from app.database import Base, engine; Base.metadata.create_all(bind=engine)"

# When Alembic is implemented, use these commands:
# alembic init alembic
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head
```

### Code Quality
```bash
# Format code with black
black app/

# Sort imports with isort
isort app/

# Lint with ruff
ruff check app/

# Type checking with mypy (when configured)
mypy app/
```

## Architecture

### High-Level Structure
CampusVault is a university resource sharing platform built with FastAPI, following a layered architecture:

- **API Layer** (`app/api/v1/`): REST endpoints organized by domain (auth, users, faculties, programs, course_units, resources, catalog, admin, notifications, activities)
- **Service Layer** (planned): Business logic and authorization checks
- **Data Access Layer** (`app/models/`): SQLAlchemy models with relationships
- **Storage Layer** (`app/storage/`): Pluggable file storage adapters (local, Google Drive, OneDrive)

### Core Domain Model
The application models a university's academic structure:

```
Faculty (e.g., Engineering, Medicine)
  ↓
Program (e.g., Computer Science, Electrical Engineering)
  ↓
CourseUnit (specific course in a year/semester)
  ↓
Resource (files shared by students)
```

### Key Models
- **User**: Students with faculty/program enrollment, JWT authentication
- **Faculty**: Top-level academic divisions (name, code)
- **Program**: Academic programs within faculties (duration_years)
- **CourseUnit**: Individual courses with year/semester constraints
- **Resource**: Uploaded files with ownership, visibility, ratings, comments
- **Activity**: User activity tracking for notifications

### Authentication & Authorization
- **JWT tokens**: Access tokens (30min) + refresh tokens (7 days)
- **API Key**: Admin-only operations via X-API-Key header
- **Ownership model**: Users manage only their own resources
- **Role-based**: STUDENT (default) and ADMIN roles

### File Storage Strategy
Pluggable storage providers via `DRIVE_PROVIDER` setting:
- **local**: Development filesystem storage
- **gdrive**: Google Drive integration via OAuth2
- **onedrive**: Microsoft OneDrive/SharePoint via Graph API

### Configuration
Environment-based configuration using Pydantic Settings:
- Database: PostgreSQL (production) or SQLite (development)
- Cache/Rate limiting: Redis
- CORS: Configurable origins for frontend integration
- File uploads: Size limits, allowed types, storage provider selection

### Current Implementation Status
This is an early-stage project with:
- Basic FastAPI structure and routing setup
- SQLAlchemy models for core entities
- JWT authentication framework
- Multiple API endpoints implemented
- Auto-table creation (Alembic migrations planned)
- Multi-provider file storage architecture designed

### Development Notes
- Tables are currently auto-created on startup; migrate to Alembic for production
- Pre-commit hooks recommended for code quality (ruff, black, isort, mypy)
- Swagger UI available at `/docs` for API testing
- Designed for strict validation using Pydantic schemas
- Redis integration planned for rate limiting and caching
<<<<<<< HEAD
=======
 
>>>>>>> 84e067b7ef0796c6bea2e385301802c632d84f36
