from sqlalchemy import event, inspect
from sqlalchemy.orm import Session
from sqlalchemy.engine import Connection
from app.models.activity import Activity, ActivityType
from app.core.context import user_id_context
from app.models.resource import Resource
from app.models.course_unit import CourseUnit
from app.models.program import Program
from app.models.faculty import Faculty
from app.models.user import User

# Mapping of Model + Operation to ActivityType and Description Template
# (ModelClass, 'insert'|'update'|'delete') -> (ActivityType, Description Template)
ACTIVITY_MAP = {
    (Resource, 'insert'): (ActivityType.resource_uploaded, "Uploaded resource: {name}"),
    (Resource, 'delete'): (ActivityType.resource_deleted, "Deleted resource: {name}"),
    (CourseUnit, 'insert'): (ActivityType.course_created, "Created course unit: {name} ({code})"),
    (CourseUnit, 'update'): (ActivityType.course_updated, "Updated course unit: {name}"),
    (CourseUnit, 'delete'): (ActivityType.course_deleted, "Deleted course unit: {name}"),
    (Program, 'insert'): (ActivityType.program_created, "Created program: {name}"),
    (Program, 'update'): (ActivityType.program_updated, "Updated program: {name}"),
    (Faculty, 'insert'): (ActivityType.faculty_created, "Created faculty: {name}"),
    (Faculty, 'update'): (ActivityType.faculty_updated, "Updated faculty: {name}"),
}

def _log_activity(mapper, connection: Connection, target, operation: str):
    """
    Generic listener to log activities based on model changes.
    """
    user_id = user_id_context.get()
    
    # If no user context (e.g. system script or unauthenticated), skip logging
    # or you could log as system (user_id=None or specific system ID)
    if not user_id:
        return

    model_class = mapper.class_
    config = ACTIVITY_MAP.get((model_class, operation))
    
    if not config:
        return

    activity_type, desc_template = config
    
    # Format description using target attributes
    try:
        # Safe formatting: convert target to dict or access attributes
        # We use getattr to be safe
        format_args = {c.key: getattr(target, c.key) for c in mapper.column_attrs}
        description = desc_template.format(**format_args)
    except Exception:
        description = f"{operation.capitalize()} {model_class.__name__}"

    # Insert directly into activities table to avoid session recursion/issues
    # We use the core insert construct
    stmt = Activity.__table__.insert().values(
        user_id=user_id,
        activity_type=activity_type,
        description=description,
        created_at=target.created_at if hasattr(target, 'created_at') else None # Let DB handle default or use target's
    )
    
    # If created_at is not in values, let DB default handle it (func.now())
    # But we need to be careful if target.created_at is None and column is nullable=False
    # The Activity model has server_default=func.now(), so omitting it is fine.
    
    connection.execute(stmt)

def register_activity_listeners():
    """
    Register SQLAlchemy event listeners for all mapped models.
    """
    for (model_class, operation), _ in ACTIVITY_MAP.items():
        if operation == 'insert':
            event.listen(model_class, 'after_insert', lambda m, c, t: _log_activity(m, c, t, 'insert'))
        elif operation == 'update':
            event.listen(model_class, 'after_update', lambda m, c, t: _log_activity(m, c, t, 'update'))
        elif operation == 'delete':
            event.listen(model_class, 'after_delete', lambda m, c, t: _log_activity(m, c, t, 'delete'))

# Auto-register when this module is imported
register_activity_listeners()
