from contextvars import ContextVar
from typing import Optional

# Context variable to store the current user ID for the request
user_id_context: ContextVar[Optional[int]] = ContextVar("user_id_context", default=None)
