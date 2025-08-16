# CampusVault – University Resource Sharing Backend

A secure, scalable backend API for university students to share educational resources, organized by Faculties → Programs → Course Units, with year/semester structure. Designed for strict authentication/authorization, robust validation, and production-ready ops.

---

## Name

Official project name: CampusVault

---

## Goals

- Strong auth (JWT + optional API key) and ownership-based access control
- Proper domain modeling for faculties, programs, course units, enrollments, and resources
- Secure file uploads to cloud drive (Google Drive or OneDrive) with strict access policies
- Discoverability via tagging, search, rating, bookmarking
- Discussion and notifications
- Observability (logging, metrics), rate limiting, and sensible defaults

---

## Tech Stack

- Framework: FastAPI
- Database: PostgreSQL (SQLAlchemy 2.x ORM, Alembic migrations)
- Auth: JWT (access/refresh), bcrypt (Passlib)
- Cache/Rate limit: Redis
- File Storage: Local filesystem (dev) OR Google Drive/OneDrive via OAuth (prod)
- Config: .env (Pydantic settings)
- Tooling: ruff, black, isort, mypy (optional), pre-commit
- Manual verification: Swagger UI (/docs)

---

## High-level Architecture

- API Layer (FastAPI routers): auth, users, faculties, programs, course units, resources, search, discussions, admin
- Service Layer: business logic (authorization checks, validations, transactional ops)
- Data Access: SQLAlchemy models and repositories
- Background Tasks: email notifications, file processing
- Caching/Rate limiting: Redis
- Storage: pluggable adapter (local, Google Drive, OneDrive)

---

## Security Model

- JWT Auth: access tokens (short-lived) + refresh tokens (longer-lived)
- Admin Access: X-API-Key header enables admin-only endpoints (no user roles stored)
- Ownership checks: users can manage only their own resources and profiles
- Rate limiting: per-IP and per-user via Redis
- CORS: configurable allowed origins
- Input Validation: strict Pydantic schemas
- Passwords: bcrypt hashing (Passlib)
- Sensitive data: never returned in API responses
- File uploads: content-type/size validation, allowed extensions; cloud drive uploads via OAuth tokens; local temp staging before upload
- Audit logs: key actions tracked (create/delete resource, admin actions)

---

## Planned Project Structure

```
app/
  main.py
  database.py
  core/
    config.py
    security.py
    dependencies.py
    rate_limit.py
    logging.py
  models/
    faculty.py
    user.py
    program.py
    course_unit.py
    enrollment.py
    tag.py
    resource.py
    bookmark.py
    rating.py
    comment.py
    notification.py
  schemas/
    common.py
    faculty.py
    user.py
    program.py
    course_unit.py
    resource.py
    tag.py
    comment.py
    rating.py
    bookmark.py
    notification.py
    auth.py
  repositories/
    faculty_repo.py
    user_repo.py
    program_repo.py
    course_unit_repo.py
    resource_repo.py
    ...
  services/
    auth_service.py
    user_service.py
    faculty_service.py
    program_service.py
    course_unit_service.py
    resource_service.py
    search_service.py
    notification_service.py
  api/
    deps.py
    v1/
      auth.py
      users.py
      faculties.py
      programs.py
      course_units.py
      resources.py
      tags.py
      bookmarks.py
      ratings.py
      comments.py
      search.py
      admin.py
  storage/
    base.py
    local_storage.py
    gdrive_storage.py
    onedrive_storage.py
  utils/
    file_handler.py
    email.py
    hashing.py
  middleware/
    request_id.py
    audit.py
alembic/
  versions/
scripts/
  seed_data.py
  create_superuser.py
requirements.txt
.env.example
README.md
```

---

## Database Model (ER overview)

- Faculty (id, name, code)
- Program (id, faculty_id -> Faculty, name, code, duration_years [e.g., 3–5])
- CourseUnit (id, program_id -> Program, name, code, year [1..duration_years], semester [1|2])
- User (id, email, username, hashed_password, created_at)
- Tag (id, name, slug)
- Resource (id, owner_id -> User, course_unit_id -> CourseUnit, title, description, storage_provider, storage_key, mime_type, size, visibility [public/private], avg_rating, created_at)
- ResourceTag (resource_id -> Resource, tag_id -> Tag)
- Bookmark (user_id -> User, resource_id -> Resource)
- Rating (user_id -> User, resource_id -> Resource, score [1..5], comment?)
- Comment (id, resource_id -> Resource, user_id -> User, body, parent_comment_id?, created_at)
- Notification (id, user_id -> User, type, payload JSON, read_at, created_at)

Indexes on frequent lookups (faculty.code, program.code, user.email, tag.slug, course_unit.program_id+year+semester, resource.course_unit_id, resource.title trigram, etc.).

---

## Environment Variables (.env)

- APP_ENV=development|staging|production
- SERVER_HOST=0.0.0.0
- SERVER_PORT=8000
- LOG_LEVEL=INFO
- DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DB
- REDIS_URL=redis://localhost:6379/0
- SECRET_KEY=change_me
- ACCESS_TOKEN_EXPIRE_MINUTES=30
- REFRESH_TOKEN_EXPIRE_DAYS=7
- JWT_ALG=HS256
- API_KEY=admin_only_operations_key
- CORS_ORIGINS=["http://localhost:3000"]

Optional institution metadata
- UNIVERSITY_NAME=Your University Name
- UNIVERSITY_CODE=YOURCODE

File storage (select one via DRIVE_PROVIDER):
- DRIVE_PROVIDER=local|gdrive|onedrive
- FILE_STORAGE_DIR=/var/lib/campusvault/files            # used when DRIVE_PROVIDER=local

Google Drive (when DRIVE_PROVIDER=gdrive)
- GDRIVE_CLIENT_ID=
- GDRIVE_CLIENT_SECRET=
- GDRIVE_REFRESH_TOKEN=                                 # or use service account
- GDRIVE_SERVICE_ACCOUNT_JSON_PATH=                     # optional alternative to refresh token
- GDRIVE_PARENT_FOLDER_ID=                              # base folder for uploads

OneDrive / Microsoft 365 (when DRIVE_PROVIDER=onedrive)
- MS_CLIENT_ID=
- MS_CLIENT_SECRET=
- MS_TENANT_ID=
- MS_REFRESH_TOKEN=
- MS_DRIVE_ID=                                          # target drive (user or SharePoint)
- MS_PARENT_FOLDER_ID=

Email (optional)
- SMTP_HOST=localhost
- SMTP_PORT=1025
- SMTP_USER=
- SMTP_PASSWORD=
- FROM_EMAIL=noreply@campusvault.test

Uploads
- MAX_UPLOAD_SIZE_MB=25
- ALLOWED_FILE_TYPES=pdf,doc,docx,ppt,pptx,txt,jpg,png

---

## API Overview (v1)

Auth
- POST /api/v1/auth/register – create account
- POST /api/v1/auth/login – get access/refresh tokens
- POST /api/v1/auth/refresh – rotate access token
- POST /api/v1/auth/logout – revoke refresh token
- GET  /api/v1/auth/me – current user profile

Users
- GET  /api/v1/users/{id}
- PATCH /api/v1/users/{id} – self updates only; API key can manage any user

Faculties
- GET  /api/v1/faculties
- POST /api/v1/faculties (API key)
- GET  /api/v1/faculties/{id}

Programs
- GET  /api/v1/programs?faculty_id=
- POST /api/v1/programs (API key)
- GET  /api/v1/programs/{id}
- GET  /api/v1/programs/{id}/course-units?year=&semester=

Course Units
- GET    /api/v1/course-units?program_id=&year=&semester=
- POST   /api/v1/course-units (API key)
- GET    /api/v1/course-units/{id}

Resources
- GET  /api/v1/resources – list (filters: faculty_id, program_id, course_unit_id, year, semester, tag, q)
- POST /api/v1/resources – create with file upload (to selected storage provider)
- GET  /api/v1/resources/{id}
- GET  /api/v1/resources/{id}/download – gated by visibility
- DELETE /api/v1/resources/{id} – owner or API key
- POST /api/v1/resources/{id}/tags – add tags

Bookmarks & Ratings
- POST   /api/v1/resources/{id}/bookmark
- DELETE /api/v1/resources/{id}/bookmark
- POST   /api/v1/resources/{id}/rating – create/update rating

Comments
- GET  /api/v1/resources/{id}/comments
- POST /api/v1/resources/{id}/comments

Search
- GET /api/v1/search?q=...&tags=...&faculty_id=...&program_id=...&year=...&semester=...

Admin
- GET    /api/v1/admin/users – requires X-API-Key
- GET    /api/v1/admin/analytics – requires X-API-Key

System
- GET /health
- GET /docs (Swagger UI)
- GET /redoc

---

## File Storage Strategy

We’ll store files in the school cloud drive linked to your email, using a provider adapter:
- Local (dev): files saved under FILE_STORAGE_DIR.
- Google Drive: OAuth 2.0 with refresh token or service account; files uploaded under a parent folder; store drive fileId as storage_key.
- OneDrive/Microsoft 365: Microsoft Graph with OAuth; store driveItem id as storage_key.

Notes
- Never store raw passwords; use OAuth tokens or service accounts.
- Keep tokens in environment variables or secret manager.
- Consider chunked uploads for large files.
- Use opaque download URLs backed by auth checks; never expose storage keys directly.

---

## Setup

PostgreSQL on VM
- Create DB and user with least privilege
- Enable daily backups and point-in-time recovery if possible

Python
- Create virtualenv
- pip install -r requirements.txt
- Copy .env.example to .env and fill in values
- Run Alembic migrations
- Start server: uvicorn app.main:app --reload

Redis
- Install and start Redis (for rate limit, cache)

Storage
- Set DRIVE_PROVIDER to local|gdrive|onedrive
- Configure corresponding credentials (.env)
- Ensure local FILE_STORAGE_DIR exists when using local

---

## Development Workflow

- Swagger-first: implement endpoints and validate via /docs
- Use pre-commit hooks (ruff/black/isort/mypy)
- Use Alembic for all schema changes
- Optional later: add pytest-based automated tests

---

## Implementation Plan (phased)

1) Bootstrap project: settings, DB session, logging, health route
2) Auth: register/login/refresh/me, password hashing, JWT
3) Core catalog: faculties, programs, course units (with year/semester) – CRUD (API key)
4) Resources: upload to selected storage provider, visibility rules, secure download, tagging
5) Bookmarks/Ratings: endpoints and aggregates
6) Comments: threads with parent_comment_id
7) Search: filters across hierarchy + text search
8) Notifications: on comments/replies (email optional)
9) Admin: API key header + dashboards/analytics
10) Hardening: rate limits, audit logs, pagination, caching

---

## Notes

- Start with local storage; switch to Google Drive/OneDrive when credentials are ready
- Keep secrets out of code; use environment variables
- Avoid returning internal IDs for storage paths; use opaque URLs with access checks
- Consider ETags/If-None-Match for downloads later

---

## License
TBD