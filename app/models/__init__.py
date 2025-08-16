# Import models here so Base.metadata.create_all can discover them
from app.models import user  # noqa: F401
from app.models import faculty  # noqa: F401
from app.models import program  # noqa: F401
from app.models import course_unit  # noqa: F401
